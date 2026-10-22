"""命令行装配入口；业务执行委托给 RunService。"""

import argparse
import uuid

from workagentharness.agents.checkpointer.provider import open_checkpointer
from workagentharness.agents.lead_agent.agent import make_lead_agent
from workagentharness.app_server.stdio_rpc import serve_stdio
from workagentharness.config.loader import load_chat_model_config
from workagentharness.execution.run_service import RunService
from workagentharness.models.factory import create_chat_model
from workagentharness.persistence.db import open_database
from workagentharness.persistence.run_repository import RunRepository
from workagentharness.persistence.session_repository import SessionRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="WorkAgentHarness 学习用 Agent")
    parser.add_argument("--config", default="config.yaml", help="YAML 配置文件")
    parser.add_argument("--db", default="data/workagentharness.db", help="SQLite 文件")
    parser.add_argument("--thread", help="继续已有 session/thread")
    parser.add_argument("--once", metavar="TEXT", help="发送一条消息后退出")
    parser.add_argument("--mode", choices=("cli", "app-server"), default="cli",
                        help="交互终端或教学用 stdio JSON-RPC 子集")
    args = parser.parse_args()

    chat_config = load_chat_model_config(args.config)
    database = open_database(args.db)
    checkpoint_conn, saver = open_checkpointer(args.db)
    try:
        model = create_chat_model(chat_config)
        agent = make_lead_agent(model, checkpointer=saver)
        sessions = SessionRepository(database)
        runs = RunRepository(database)
        service = RunService(agent, sessions, runs)
        if args.mode == "app-server":
            # App Server 与 CLI 共用装配好的 service，协议层不直接操作 Agent。
            serve_stdio(service, sessions)
            return

        session_id = args.thread or uuid.uuid4().hex
        owner_id = "local-user"  # 用户鉴权将在治理篇建立；这里先显式保留字段
        sessions.create(session_id, owner_id)

        if args.once is not None:
            _execute_and_print(service, owner_id, session_id, args.once)
            return

        print(f"WorkAgentHarness · thread={session_id} · 输入 /exit 退出")
        while True:
            try:
                text = input("你> ").strip()
            except EOFError:
                break
            if text in {"/exit", "/quit"}:
                break
            if not text:
                continue
            _execute_and_print(service, owner_id, session_id, text)
    finally:
        checkpoint_conn.close()  # Checkpointer 连接由入口统一关闭
        database.close()         # 业务数据库连接也在这里释放


def _execute_and_print(service: RunService, owner_id: str, session_id: str, text: str) -> None:
    """把应用服务结果翻译成终端文本；不在这里直接调用模型。"""
    result = service.execute(owner_id, session_id, text)
    print(f"thread={session_id} run={result.run_id}")
    if result.status == "completed":
        print(f"助手> {result.answer}")
    else:
        print(f"运行失败 ({result.error_code}, run={result.run_id})")


if __name__ == "__main__":
    main()

