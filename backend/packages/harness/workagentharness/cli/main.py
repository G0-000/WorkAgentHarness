"""命令行装配入口；业务执行委托给 RunService。

本文件是整个应用的"组合根（composition root）"：
    - 解析命令行参数
    - 依次构造所有依赖（配置、数据库、checkpointer、模型、Agent、Repository、RunService）
    - 按 --mode 选择交互终端 CLI 或 stdio App Server
    - 在 finally 里统一释放数据库连接

核心原则：本文件不写任何业务规则；业务一律委托给 RunService。
这样以后加 HTTP API、MCP 入口时，只需再写一个入口函数做同样的装配，
RunService、Agent、Repository 完全复用。
"""

import argparse
import logging
import uuid

# ── 依赖清单：每个 import 对应一个被装配的组件 ──────────────────────────────
# 以下顺序就是 main() 里的装配顺序，不要随意调整
from workagentharness.agents.checkpointer.provider import open_checkpointer
from workagentharness.agents.lead_agent.agent import make_lead_agent
from workagentharness.app_server.stdio_rpc import serve_stdio
from workagentharness.config.loader import load_chat_model_config
from workagentharness.execution.run_service import RunService
from workagentharness.events.sse import EventBuffer, sse_event_stream
from workagentharness.middleware import ToolAuditMiddleware
from workagentharness.models.factory import create_chat_model
from workagentharness.persistence.db import open_database
from workagentharness.persistence.run_repository import RunRepository
from workagentharness.persistence.session_repository import SessionRepository
from workagentharness.tools.builtins import default_catalog


def main() -> None:
    # ── 第 1 步：解析命令行参数 ────────────────────────────────────────────
    parser = argparse.ArgumentParser(description="WorkAgentHarness 学习用 Agent")
    parser.add_argument("--config", default="config.yaml",
                        help="YAML 配置文件路径，默认 ./config.yaml")
    parser.add_argument("--db", default="data/workagentharness.db",
                        help="SQLite 数据库文件路径，业务表和 checkpoint 共用同一文件")
    parser.add_argument("--thread",
                        help="继续已有 session/thread；不传则新建一个随机 thread_id")
    parser.add_argument("--once", metavar="TEXT",
                        help="发送一条消息后立即退出（脚本化/自动化用）")
    parser.add_argument("--stream", action="store_true",
                        help="流式输出事件（第 10 章）：逐条打印文本增量与工具活动")
    parser.add_argument("--sse", action="store_true",
                        help="把事件按 SSE 格式打印（第 10.2 节）；可与 --stream 互换")
    parser.add_argument("--mode", choices=("cli", "app-server"), default="cli",
                        help="cli=交互终端；app-server=教学用 stdio JSON-RPC 子集")
    args = parser.parse_args()

    # 工具审计中间件默认只在 WARNING 级别输出（工具失败时可见），避免刷屏
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")

    # ── 第 2 步：装配依赖（组合根核心）──────────────────────────────────────
    # 顺序固定：配置 → 业务库 → checkpoint → 模型 → Agent → Repository → Service
    # 任何一步失败都会抛异常并退出，不会留下半初始化状态。
    chat_config = load_chat_model_config(args.config)       # YAML → 类型化 ChatModelConfig
    database = open_database(args.db)                        # 业务库：sessions/messages/runs
    # saver 就是 Agent 的"存档器"：每次 invoke 后把图状态存进 SQLite，
    # 下次用同一个 thread_id 再调时自动读回，实现"接着上次继续聊"。
    checkpoint_conn, saver = open_checkpointer(args.db)     # checkpoint 长连接 + LangGraph 存档器
    try:
        # 注意：database 和 checkpoint_conn 指向同一个 .db 文件，
        # 但 schema 完全不同——业务表由 schema.py 建，checkpoint 表由 saver.setup() 建。
        model = create_chat_model(chat_config)             # fake / openai-compatible 二选一

        # 第三篇新增：装配工具目录（计算 + 只读文件），把工具交给 Agent
        catalog = default_catalog()
        tools = catalog.langchain_tools()                  # 交给 create_agent 的工具列表
        agent = make_lead_agent(
            model,
            tools=tools,                                   # 关键变化：从 [] 变成真实工具
            middleware=[ToolAuditMiddleware()],            # 工具调用审计（第 9 章）
            checkpointer=saver,
        )
        sessions = SessionRepository(database)             # 业务会话/消息 Repository
        runs = RunRepository(database)                     # run 状态机 Repository
        service = RunService(agent, sessions, runs)        # 核心用例：编排一次对话的完整生命周期

        # ── 第 3 步：按入口模式分派 ────────────────────────────────────────
        if args.mode == "app-server":
            # App Server 与 CLI 共用上面装配好的同一个 service 实例。
            # stdio_rpc 只做 JSON 协议解析，不直接 new Agent / 不开数据库。
            # 执行完 serve_stdio 不会返回（它循环读 stdin），直到 EOF 或外部 kill。
            serve_stdio(service, sessions)
            return

        # ── 第 4 步：CLI 模式 ─────────────────────────────────────────────
        # thread_id 同时是业务 session_id 和 LangGraph checkpoint 恢复键。
        # 传了 --thread 就恢复历史；不传就新建随机 id。
        session_id = args.thread or uuid.uuid4().hex
        owner_id = "local-user"  # 用户鉴权留到治理篇；本地单机先硬编码占位
        sessions.create(session_id, owner_id)   # INSERT OR IGNORE，重复创建不报错

        # --once 模式：执行一次就退出（适合脚本调用和自动化测试）
        if args.once is not None:
            if args.sse:
                _execute_sse_and_print(service, owner_id, session_id, args.once)
            elif args.stream:
                _execute_stream_and_print(service, owner_id, session_id, args.once)
            else:
                _execute_and_print(service, owner_id, session_id, args.once)
            return

        # 交互模式：循环读 input()，直到 /exit、/quit 或 EOF（Ctrl+D）
        print(f"WorkAgentHarness · thread={session_id} · 输入 /exit 退出")
        while True:
            try:
                text = input("你> ").strip()
            except EOFError:       # Ctrl+D 或管道关闭时优雅退出
                break
            if text in {"/exit", "/quit"}:
                break
            if not text:           # 空输入直接跳过，不触发模型调用
                continue
            if args.sse:
                _execute_sse_and_print(service, owner_id, session_id, text)
            elif args.stream:
                _execute_stream_and_print(service, owner_id, session_id, text)
            else:
                _execute_and_print(service, owner_id, session_id, text)
    finally:
        # 无论正常退出、Ctrl+C、还是异常，两个连接都必须关闭。
        # 顺序无强约束（两者是同一文件的不同连接），但保持先 checkpoint 后业务库。
        checkpoint_conn.close()
        database.close()


def _execute_and_print(service: RunService, owner_id: str, session_id: str, text: str) -> None:
    """把 RunService 的结构化结果翻译成终端文本输出。

    职责边界：
        - 本函数只做"结果 → print"的翻译，不直接调用 model / agent。
        - 失败时打印 error_code（异常类型名），不打印异常原文（可能含敏感信息）。
    """
    result = service.execute(owner_id, session_id, text)
    print(f"thread={session_id} run={result.run_id}")
    if result.status == "completed":
        print(f"助手> {result.answer}")
    else:
        # failed / cancelled：只打印错误类别，不打印 str(exc)
        print(f"运行失败 ({result.error_code}, run={result.run_id})")


def _execute_stream_and_print(
    service: RunService, owner_id: str, session_id: str, text: str
) -> None:
    """消费事件流并逐条打印（第 10 章的终端消费方）。

    事件 → 终端的映射：
        run_start   → 打印 thread / run
        text_delta  → 立即输出，不换行（形成"打字机"效果）
        tool_call   → 单独一行显示工具名和参数
        tool_result → 单独一行显示工具名和成功与否
        run_end     → 换行后打印最终结果或错误类别
    """
    for event in service.execute_stream(owner_id, session_id, text):
        event_type = event.get("type")
        if event_type == "run_start":
            print(f"thread={event['thread_id']} run={event['run_id']}")
        elif event_type == "text_delta":
            print(event.get("text", ""), end="", flush=True)
        elif event_type == "tool_call":
            print(f"\n[工具调用] {event.get('name')} args={event.get('args')}")
        elif event_type == "tool_result":
            print(f"[工具结果] {event.get('name')} ok={event.get('ok')}")
        elif event_type == "run_end":
            if event.get("status") == "completed":
                print()                       # 文本增量已打完，补一个换行
            elif event.get("status") == "cancelled":
                print("\n运行已取消")
            else:
                print(f"\n运行失败 ({event.get('error_code')})")


def _execute_sse_and_print(
    service: RunService, owner_id: str, session_id: str, text: str
) -> None:
    """把事件按 SSE 文本打印（第 10.2 节的 SSE 消费方）。

    与 ``_execute_stream_and_print`` 共用同一套事件，只换编码：
    终端看"打字机"，SSE 看"协议帧"。要接 HTTP 时，把这里的 print
    换成 ``StreamingResponse`` 的 yield 即可，事件结构不动。
    """
    buffer = EventBuffer()
    for chunk in sse_event_stream(service.execute_stream(owner_id, session_id, text), buffer=buffer):
        # SSE 帧本身以空行结束，这里再补一个分隔便于终端观察
        print(chunk, end="" if chunk.endswith("\n\n") else "\n")


if __name__ == "__main__":
    # 通过 `uv run workagentharness` 命令行入口（pyproject.toml [project.scripts]）启动
    main()
