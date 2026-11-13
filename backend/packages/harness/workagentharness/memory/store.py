"""两级记忆存储（对齐 EvoFlow ``agents/memory/agent_memory.py``）。

原版符号（快照 8e462a37）：
    AgentMemoryManager              ← :13
    load_agent_memory               ← :55
    save_agent_memory               ← :72
    load_task_memory                ← :88
    save_task_memory                ← :108
    get_combined_memory             ← :125
    clear_task_memory               ← :143
    add_fact_to_agent_memory        ← :157
    add_to_task_history             ← :177

本项目偏差（有意）：
    原版落在 Owned KB 的 ``mem_*`` 表；本仓没有知识库（第五篇再做），
    因此复用同一 SQLite 文件，新建 ``agent_memory`` / ``task_memory`` 两张表。
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable

from workagentharness.memory.entities import EntityRef
from workagentharness.memory.schema import ensure_memory_tables

ALLOWED_CATEGORIES = ("preference", "behavior", "context", "knowledge", "goal")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fact_id(content: str, entity: EntityRef) -> str:
    raw = f"{entity.entity_type}:{entity.entity_id}:{content}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


class MemoryStore:
    """长期（agent 级）+ 短期（thread 级）两级记忆。"""

    def __init__(self, connection: sqlite3.Connection, *, agent_name: str = "default") -> None:
        self.connection = connection
        self.agent_name = agent_name
        ensure_memory_tables(connection)

    # ---------- 长期 ----------
    def add_fact(
        self,
        content: str,
        *,
        category: str = "preference",
        confidence: float = 1.0,
        entity: EntityRef | None = None,
    ) -> str:
        """写一条长期事实（同名内容同实体自动覆盖，保证幂等）。"""
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"未知的记忆分类: {category}")
        if not 0.0 <= float(confidence) <= 1.0:
            raise ValueError("confidence 必须在 0 到 1 之间")
        text = (content or "").strip()
        if not text:
            raise ValueError("记忆内容不能为空")
        entity = entity or EntityRef("user", "local-user")
        fact_id = _fact_id(text, entity)
        self.connection.execute(
            "INSERT INTO agent_memory(id, agent_name, content, category, confidence, entity_type, entity_id, created_at) "
            "VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET confidence=excluded.confidence, category=excluded.category, created_at=excluded.created_at",
            (fact_id, self.agent_name, text, category, float(confidence), entity.entity_type, entity.entity_id, _now()),
        )
        self.connection.commit()
        return fact_id

    def facts(
        self,
        *,
        entity: EntityRef | None = None,
        categories: Iterable[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """按实体读长期记忆（不同实体互不可见）。"""
        entity = entity or EntityRef("user", "local-user")
        sql = (
            "SELECT id, content, category, confidence, entity_type, entity_id, created_at "
            "FROM agent_memory WHERE agent_name=? AND entity_type=? AND entity_id=?"
        )
        params: list[Any] = [self.agent_name, entity.entity_type, entity.entity_id]
        if categories:
            marks = ",".join("?" for _ in categories)
            sql += f" AND category IN ({marks})"
            params.extend(list(categories))
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(int(limit))
        rows = self.connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def delete_fact(self, fact_id: str) -> bool:
        """删一条长期事实（原版 ``delete_memory_fact``）；不存在返回 False。"""
        cursor = self.connection.execute("DELETE FROM agent_memory WHERE id=?", (fact_id,))
        self.connection.commit()
        return cursor.rowcount > 0

    # ---------- 短期 ----------
    def add_task_note(self, thread_id: str, role: str, content: str) -> None:
        """追加一条任务内记录（原版 ``add_to_task_history``）。"""
        self.connection.execute(
            "INSERT INTO task_memory(thread_id, role, content, created_at) VALUES (?,?,?,?)",
            (thread_id, role, (content or "").strip(), _now()),
        )
        self.connection.commit()

    def task_notes(self, thread_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT role, content, created_at FROM task_memory WHERE thread_id=? ORDER BY id",
            (thread_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def clear_task_memory(self, thread_id: str) -> int:
        """任务结束清理短期记忆，返回删除条数（原版 ``clear_task_memory``）。"""
        cursor = self.connection.execute("DELETE FROM task_memory WHERE thread_id=?", (thread_id,))
        self.connection.commit()
        return cursor.rowcount

    # ---------- 合并视图 ----------
    def get_combined_memory(self, thread_id: str | None = None, *, entity: EntityRef | None = None) -> dict[str, Any]:
        """一次拿到两级（原版 ``get_combined_memory``），并给出合并文本。"""
        long_term = self.facts(entity=entity, limit=50)
        short_term = self.task_notes(thread_id) if thread_id else []
        merged_lines = [f"[long] {row['content']}" for row in long_term]
        merged_lines += [f"[{row['role']}] {row['content']}" for row in short_term]
        return {
            "long_term": long_term,
            "short_term": short_term,
            "merged": "\n".join(merged_lines),
        }


__all__ = ["ALLOWED_CATEGORIES", "MemoryStore"]
