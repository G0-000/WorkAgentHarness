"""一次 Agent 调用的 run 生命周期编排。

RunService 是核心用例层（application service）：
    - 把"用户发一条消息 → Agent 回复"这件事的完整生命周期管起来
    - 同时写业务消息（SessionRepository）和 run 状态（RunRepository）
    - 统一处理成功/失败/中断三种终态
    - CLI 和 App Server 两个入口都调用这同一个类，不各自重复业务逻辑

核心原则：本类不直接操作数据库、不直接调用 LangChain 细节；
所有依赖通过构造函数注入（agent / sessions / runs），便于测试和替换。
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterator
from uuid import uuid4

from workagentharness.events.stream import Event, stream_agent_run


def _now_utc() -> str:
    """统一用 UTC ISO 8601 时间戳，避免不同机器本地时区混入排序字段。"""
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class RunResult:
    """一次执行的结构化结果，入口层（CLI/stdio）只读这个，不关心 Agent 内部。

    字段说明：
        run_id:     本次执行的唯一标识，可用于查数据库
        status:     终态：completed / failed / cancelled
        answer:     成功时的助手回复文本
        error_code: 失败时的错误类别（异常类型名，不是异常原文）
    """
    run_id: str
    status: str
    answer: str = ""
    error_code: str = ""


class RunService:
    """把 Agent、消息记录和 run 状态放在同一应用用例中。

    依赖全部由构造函数注入：
        - agent:    已构造好的 LangGraph Agent（带 checkpointer）
        - sessions: SessionRepository（业务消息/会话读写）
        - runs:     RunRepository（run 状态机）
    """

    def __init__(self, agent, sessions, runs) -> None:
        self._agent = agent
        self._sessions = sessions
        self._runs = runs

    def execute(self, owner_id: str, session_id: str, text: str) -> RunResult:
        """执行一次完整对话轮次：用户消息 → Agent → 助手回复 → 写终态。

        参数：
            owner_id:   所属用户（本地版硬编码 "local-user"）
            session_id: 会话 ID，同时作为 LangGraph checkpoint 的 thread_id
            text:       用户输入文本

        返回：
            RunResult 结构化结果，入口层据此打印/返回响应。
        """
        # ── 输入边界校验：空文本在调用模型前直接拒绝，不建 run ─────────────
        if not text.strip():
            raise ValueError("用户输入不能为空")

        # ── 创建 run 记录：每次执行单独编号，重试不复用旧 id ───────────────
        run_id = uuid4().hex
        self._runs.start(run_id, session_id, owner_id, _now_utc())

        try:
            # 1. 先写用户消息到业务历史
            # 注意：这一步也纳入生命周期——如果数据库写入失败，
            # 下面的 except Exception 会捕获并把 run 标成 failed，
            # 不会留下一个永远 running 的孤儿记录。
            self._sessions.add_message(session_id, "user", text)

            # 2. 调用 Agent（LangGraph 图）
            #    thread_id=session_id → LangGraph 自动从 checkpoint 恢复历史
            #    输入形状是消息列表，符合 create_agent 的契约
            result = self._agent.invoke(
                {"messages": [("user", text)]},
                {"configurable": {"thread_id": session_id}},
            )

            # 3. 从图结果中取最后一条消息作为助手回复
            answer = str(result["messages"][-1].content)

            # 4. 写助手回复到业务历史
            self._sessions.add_message(session_id, "assistant", answer)

            # 5. run 标记为完成
            self._runs.complete(run_id, _now_utc())
            return RunResult(run_id=run_id, status="completed", answer=answer)

        except KeyboardInterrupt:
            # 用户按 Ctrl+C：先把 run 标成 cancelled，再把异常重新抛给入口
            # （入口 CLI 需要知道是中断，才能正确退出）
            self._runs.cancel(run_id, _now_utc())
            raise

        except Exception as exc:  # noqa: BLE001 - 边界层统一转换为失败终态
            # 失败时只存异常类型名（如 ValueError / ConnectionError），
            # 不存 str(exc)——因为异常原文可能含用户输入或 API 错误细节。
            # 这是"错误类别"而非"错误原文"的设计。
            error_code = type(exc).__name__
            self._runs.fail(run_id, error_code, _now_utc())
            return RunResult(run_id=run_id, status="failed", error_code=error_code)

    def execute_stream(self, owner_id: str, session_id: str, text: str) -> Iterator[Event]:
        """流式执行：边跑边发事件，同时保证与同步版一致的 run 生命周期。

        与 execute 的区别只有一点：
            execute 等 Agent 跑完再返回整段回答；
            execute_stream 用生成器边收事件边 yield 给入口。

        生命周期完全一致（都在同一个 try/except 里）：
            run_start → 写 user 消息 → 逐个 yield 事件 → 写 assistant 消息
            → run_end(completed)；异常 → run_end(failed)；Ctrl+C → cancelled。

        参数与 execute 相同；产出的事件：
            {"type": "run_start", "run_id", "thread_id"}
            {"type": "text_delta", "text"}
            {"type": "tool_call", "name", "args"}
            {"type": "tool_result", "name", "ok"}
            {"type": "run_end", "status", "answer" / "error_code"}
        """
        # 输入边界校验与同步版一致：空文本不建 run
        if not text.strip():
            raise ValueError("用户输入不能为空")

        run_id = uuid4().hex
        self._runs.start(run_id, session_id, owner_id, _now_utc())
        yield {"type": "run_start", "run_id": run_id, "thread_id": session_id}

        try:
            # 1. 用户消息入库（失败会进入下面的 except，run 变成 failed）
            self._sessions.add_message(session_id, "user", text)

            # 2. 消费事件流，同时把文本增量拼起来当作最终回答
            #    （流式下没有"最后一条消息"，只能靠拼接）
            answer_parts: list[str] = []
            for event in stream_agent_run(self._agent, [("user", text)], thread_id=session_id):
                if event.get("type") == "text_delta":
                    answer_parts.append(event.get("text", ""))
                yield event

            answer = "".join(answer_parts).strip()

            # 3. 助手回答入库 + run 完成
            self._sessions.add_message(session_id, "assistant", answer)
            self._runs.complete(run_id, _now_utc())
            yield {"type": "run_end", "status": "completed", "answer": answer}

        except KeyboardInterrupt:
            self._runs.cancel(run_id, _now_utc())
            yield {"type": "run_end", "status": "cancelled"}
            raise

        except Exception as exc:  # noqa: BLE001 - 与同步版保持同一失败语义
            error_code = type(exc).__name__
            self._runs.fail(run_id, error_code, _now_utc())
            yield {"type": "run_end", "status": "failed", "error_code": error_code}
