"""Run 状态的有限状态转移。"""

import sqlite3


class RunRepository:
    """封装 run 表写入；只允许一个 running run 结束一次。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def start(self, run_id: str, session_id: str, owner_id: str, now: str) -> None:
        self._conn.execute(
            "INSERT INTO runs(id, session_id, owner_id, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'running', ?, ?)",
            (run_id, session_id, owner_id, now, now),
        )
        self._conn.commit()

    def finish(self, run_id: str, status: str, now: str, error_code: str = "") -> None:
        if status not in {"completed", "failed", "cancelled"}:
            raise ValueError(f"非法 run 终态: {status}")
        cursor = self._conn.execute(
            "UPDATE runs SET status = ?, error_code = ?, updated_at = ? "
            "WHERE id = ? AND status = 'running'",
            (status, error_code, now, run_id),
        )
        self._conn.commit()
        if cursor.rowcount != 1:
            raise RuntimeError(f"run 不存在或已经结束: {run_id}")

    def complete(self, run_id: str, now: str) -> None:
        self.finish(run_id, "completed", now)

    def cancel(self, run_id: str, now: str) -> None:
        self.finish(run_id, "cancelled", now)

    def fail(self, run_id: str, error_code: str, now: str) -> None:
        self.finish(run_id, "failed", now, error_code)

