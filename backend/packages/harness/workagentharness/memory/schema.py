"""记忆与资产相关表（第 15–17 章）。

为什么单独建表而不改 ``persistence/schema.py``：
    ``sessions/messages/runs`` 是"业务记录"，这里是"提炼后的记忆与产物"，
    写入者与生命周期不同（原版也是另一套 ``mem_*`` 表）。分脚本建表，
    既不碰第三篇已有 schema，也能在同一数据库文件里做 join。
"""

from __future__ import annotations

import sqlite3

MEMORY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_memory (
    id           TEXT PRIMARY KEY,
    agent_name   TEXT NOT NULL,
    content      TEXT NOT NULL,
    category     TEXT NOT NULL,
    confidence   REAL NOT NULL,
    entity_type  TEXT NOT NULL,
    entity_id    TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id   TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_task_memory_thread ON task_memory(thread_id);

CREATE TABLE IF NOT EXISTS run_wrapups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    thread_id   TEXT NOT NULL,
    outcome     TEXT NOT NULL,
    reflection  TEXT NOT NULL DEFAULT '',
    initiatives TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id          TEXT PRIMARY KEY,
    state_key   TEXT NOT NULL UNIQUE,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    path        TEXT NOT NULL,
    size        INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);
"""


def ensure_memory_tables(connection: sqlite3.Connection) -> None:
    """幂等建表；在 ``open_database`` 之后调用即可。"""
    connection.executescript(MEMORY_SCHEMA_SQL)
    connection.commit()


__all__ = ["MEMORY_SCHEMA_SQL", "ensure_memory_tables"]
