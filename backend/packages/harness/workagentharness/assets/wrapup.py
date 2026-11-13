"""事项与反思落库（第 17 章）。

对齐 EvoFlow ``tools/builtins/proactive_submit_work_tool.py``（快照 8e462a37）：
    @tool("proactive_submit_work")  ← :102
    reflection: str = ""            ← :107
    phase=wrap_up 写 outcome / reflection / initiatives  ← :117 文档串

偏差：原版四类写入（experience / process / reflection / preferences）进
Entity Asset Hub；本项目单表 ``run_wrapups`` 只存收尾三件套。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from workagentharness.memory.schema import ensure_memory_tables


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_wrapup(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    thread_id: str,
    outcome: str,
    reflection: str = "",
    initiatives: str = "",
) -> int:
    """写一条交班记录，返回自增 id。"""
    if not str(outcome or "").strip():
        raise ValueError("outcome 不能为空（交班必须写清这一轮做成了什么）")
    ensure_memory_tables(connection)
    cursor = connection.execute(
        "INSERT INTO run_wrapups(run_id, thread_id, outcome, reflection, initiatives, created_at) VALUES (?,?,?,?,?,?)",
        (
            str(run_id),
            str(thread_id),
            str(outcome).strip(),
            str(reflection or "").strip(),
            str(initiatives or "").strip(),
            _now(),
        ),
    )
    connection.commit()
    return int(cursor.lastrowid or 0)


def list_wrapups(connection: sqlite3.Connection, *, thread_id: str | None = None) -> list[dict[str, Any]]:
    ensure_memory_tables(connection)
    if thread_id:
        rows = connection.execute(
            "SELECT id, run_id, thread_id, outcome, reflection, initiatives, created_at "
            "FROM run_wrapups WHERE thread_id=? ORDER BY id",
            (thread_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT id, run_id, thread_id, outcome, reflection, initiatives, created_at "
            "FROM run_wrapups ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


__all__ = ["list_wrapups", "record_wrapup"]
