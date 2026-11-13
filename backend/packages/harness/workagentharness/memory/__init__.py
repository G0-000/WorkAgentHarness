"""记忆层（第四篇第 15–16 章）。

对应 EvoFlow：
    agents/memory/agent_memory.py  ← store.py
    agents/memory/prompt.py        ← extract.py（规则抽取）+ injection.py（注入过滤）
    agents/middlewares/*memory*    ← middleware.py

有意偏差：
    原版记忆落 Owned KB 的 ``mem_*`` 表，本项目先落同库 SQLite 两张表；
    原版用模型抽取并做 thread 级冻结缓存，本项目用规则抽取、每 thread 注入一次。
"""

from __future__ import annotations

from workagentharness.memory.entities import EntityRef
from workagentharness.memory.extract import FactCandidate, extract_facts, should_persist_long_term
from workagentharness.memory.injection import format_memory_for_injection, standing_fact_allowed
from workagentharness.memory.middleware import MEMORY_MESSAGE_NAME, MemoryRuntimeMiddleware
from workagentharness.memory.store import MemoryStore

__all__ = [
    "MEMORY_MESSAGE_NAME",
    "EntityRef",
    "FactCandidate",
    "MemoryRuntimeMiddleware",
    "MemoryStore",
    "extract_facts",
    "format_memory_for_injection",
    "should_persist_long_term",
    "standing_fact_allowed",
]
