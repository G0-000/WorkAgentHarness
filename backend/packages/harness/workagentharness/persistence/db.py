"""统一打开业务 SQLite 数据库并初始化本项目表。

同一个 .db 文件里其实住着两套互不相干的表：

    data/workagentharness.db
    ├── sessions / messages / runs   ← 业务表，由这里的 SCHEMA_SQL 建
    └── checkpoints / checkpoint_blobs / ... ← LangGraph 内部表，由 saver.setup() 建

"同一个文件"不等于"同一套数据"：业务表给 UI 查历史，checkpoint 表给图恢复状态，
写入者、格式、生命周期都不同（见 4.1 / 4.2）。
"""

import sqlite3
from pathlib import Path

from workagentharness.persistence.schema import SCHEMA_SQL


def open_database(db_path: str) -> sqlite3.Connection:
    """连接 SQLite、设置外键/WAL，并幂等创建业务表。"""
    # 首次运行时 data/ 目录还不存在；parents=True 允许建多级目录
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # check_same_thread=False：连接可能被 CLI 主线程与入口层复用，
    # 关掉线程检查由调用方负责串行化（本项目是单线程最小闭环）
    conn = sqlite3.connect(db_path, check_same_thread=False)

    # 让查询结果支持按列名取值（row["id"]），而不是只能按下标 row[0]
    conn.row_factory = sqlite3.Row

    # WAL：写不阻塞读，读不阻塞写；对"一边跑 Agent 一边查历史"的场景更合适
    conn.execute("PRAGMA journal_mode=WAL")

    # SQLite 默认不强制外键（ON DELETE CASCADE / REFERENCES 形同注释），必须显式打开
    conn.execute("PRAGMA foreign_keys=ON")

    # 三张表全部是 CREATE TABLE IF NOT EXISTS，重复执行安全，不需要迁移框架
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
