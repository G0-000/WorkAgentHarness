"""SQLite-backed LangGraph checkpoint provider。"""

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


def open_checkpointer(db_path: str) -> tuple[sqlite3.Connection, SqliteSaver]:
    """创建长期连接与 checkpointer；调用方负责最终关闭连接。"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    saver = SqliteSaver(conn)
    saver.setup()  # 由 LangGraph saver 建立它自己管理的 checkpoint 表
    return conn, saver

