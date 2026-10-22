"""会话与业务消息 Repository。"""

import sqlite3
from datetime import UTC, datetime


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


class SessionRepository:
    """只负责可查询的业务历史，不读取 LangGraph 内部 checkpoint。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, session_id: str, owner_id: str) -> None:
        stamp = _now_utc()
        self._conn.execute(
            "INSERT OR IGNORE INTO sessions(id, owner_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, owner_id, stamp, stamp),
        )
        self._conn.commit()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        stamp = _now_utc()
        self._conn.execute(
            "INSERT INTO messages(session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, stamp),
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (stamp, session_id),
        )
        self._conn.commit()

    def list_messages(self, session_id: str, owner_id: str) -> list[sqlite3.Row]:
        """按消息顺序读取；通过 owner 条件避免仅凭 id 跨用户读取。"""
        return list(self._conn.execute(
            "SELECT m.id, m.role, m.content, m.created_at "
            "FROM messages AS m JOIN sessions AS s ON s.id = m.session_id "
            "WHERE m.session_id = ? AND s.owner_id = ? ORDER BY m.id",
            (session_id, owner_id),
        ))

