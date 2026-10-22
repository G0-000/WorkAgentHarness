"""统一打开业务 SQLite 数据库并初始化本项目表。"""

import sqlite3
from pathlib import Path

from workagentharness.persistence.schema import SCHEMA_SQL


def open_database(db_path: str) -> sqlite3.Connection:
    """连接 SQLite、设置外键/WAL，并幂等创建业务表。"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn

