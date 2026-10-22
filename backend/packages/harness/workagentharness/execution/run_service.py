"""一次 Agent 调用的 run 生命周期编排。"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class RunResult:
    run_id: str
    status: str
    answer: str = ""
    error_code: str = ""


class RunService:
    """把 Agent、消息记录和 run 状态放在同一应用用例中。"""

    def __init__(self, agent, sessions, runs) -> None:
        self._agent = agent
        self._sessions = sessions
        self._runs = runs

    def execute(self, owner_id: str, session_id: str, text: str) -> RunResult:
        if not text.strip():
            raise ValueError("用户输入不能为空")

        run_id = uuid4().hex
        self._runs.start(run_id, session_id, owner_id, _now_utc())
        try:
            # 把用户消息写入也纳入生命周期处理；否则数据库失败会留下 running run。
            self._sessions.add_message(session_id, "user", text)
            result = self._agent.invoke(
                {"messages": [("user", text)]},
                {"configurable": {"thread_id": session_id}},
            )
            answer = str(result["messages"][-1].content)
            self._sessions.add_message(session_id, "assistant", answer)
            self._runs.complete(run_id, _now_utc())
            return RunResult(run_id=run_id, status="completed", answer=answer)
        except KeyboardInterrupt:
            self._runs.cancel(run_id, _now_utc())
            raise
        except Exception as exc:  # noqa: BLE001 - 边界层统一转换为失败终态
            error_code = type(exc).__name__  # 避免原样记录可能含敏感内容的错误
            self._runs.fail(run_id, error_code, _now_utc())
            return RunResult(run_id=run_id, status="failed", error_code=error_code)

