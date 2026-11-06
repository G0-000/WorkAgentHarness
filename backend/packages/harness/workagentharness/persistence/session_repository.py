"""会话与业务消息 Repository。

本类负责"可查询的业务历史"：
    - sessions 表：会话（一次聊天对话）
    - messages 表：每条消息（用户说的、助手回的）

它**不读 LangGraph 内部 checkpoint**——那是 Agent 图状态，归 checkpointer 管。
本类只管 UI 能展示、API 能查询的业务数据。
"""

import sqlite3
from datetime import UTC, datetime


def _now_utc() -> str:
    """统一用 UTC ISO 8601 时间戳，避免不同机器本地时区混入排序字段。"""
    return datetime.now(UTC).isoformat()


class SessionRepository:
    """会话与业务消息的数据访问类。

    职责边界：
        - 只管 sessions / messages 两张业务表
        - 不碰 LangGraph checkpoint 内部表
        - 不写业务逻辑（比如不判断"该不该回复"），只做 CRUD

    依赖全部由构造函数注入：
        - conn: 已打开的 SQLite 连接（由 cli/main.py 装配层创建并关闭）
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        # 连接由入口持有并在退出时 close，本类不自己开连接、不自己关连接
        self._conn = conn

    def create(self, session_id: str, owner_id: str) -> None:
        """创建一条会话记录。

        参数：
            session_id: 会话 ID（UUID hex，同时也是 LangGraph checkpoint 的 thread_id）
            owner_id:   会话主人标识（本地版硬编码 "local-user"）

        用 INSERT OR IGNORE：重复创建同 ID 不报错，幂等。
        """
        stamp = _now_utc()
        self._conn.execute(
            "INSERT OR IGNORE INTO sessions(id, owner_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            # 参数化 SQL，禁止拼接输入，防 SQL 注入
            (session_id, owner_id, stamp, stamp),
        )
        self._conn.commit()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """往会话里加一条消息，同时更新会话的最后活跃时间。

        参数：
            session_id: 属于哪条会话
            role:       消息角色："user"（用户说的）/ "assistant"（助手回的）
            content:    消息文本内容

        做两件事：
            1. 往 messages 表插一条消息
            2. 更新 sessions 表的 updated_at（这样按时间排序会话列表时能看到最近聊过）
        """
        stamp = _now_utc()
        # 1. 插入消息
        self._conn.execute(
            "INSERT INTO messages(session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, stamp),
        )
        # 2. 更新会话最后活跃时间
        self._conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (stamp, session_id),
        )
        self._conn.commit()

    def list_messages(self, session_id: str, owner_id: str) -> list[sqlite3.Row]:
        """按消息顺序读取某个会话的全部历史消息。

        参数：
            session_id: 要读哪个会话
            owner_id:   谁在读——用于权限校验

        关键安全设计：JOIN sessions 表并校验 owner_id。
        即使你猜到了别人的 session_id，不知道 owner_id 也读不到消息。
        这叫"防跨用户读取"。

        返回：按消息 id 升序排列的列表（先发的消息在前）。
        """
        return list(self._conn.execute(
            "SELECT m.id, m.role, m.content, m.created_at "
            "FROM messages AS m JOIN sessions AS s ON s.id = m.session_id "
            # WHERE 同时校验 session_id 和 owner_id，双重条件
            "WHERE m.session_id = ? AND s.owner_id = ? ORDER BY m.id",
            (session_id, owner_id),
        ))
