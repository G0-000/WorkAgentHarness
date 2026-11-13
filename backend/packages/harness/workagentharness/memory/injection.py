"""记忆注入过滤与格式化（对齐 EvoFlow ``agents/memory/prompt.py``）。

原版符号（快照 8e462a37）：
    _standing_fact_allowed      ← prompt.py:219
    format_memory_for_injection ← prompt.py:249
    get_frozen_standing_memory  ← agents/memory/standing_freeze.py:17（本项目不做冻结）

"提示注入"在本章指**注入过滤**：决定哪条记忆能进提示词，不是防恶意 prompt injection。
"""

from __future__ import annotations

from typing import Any, Iterable

from workagentharness.memory.extract import FactCandidate

# 注入时允许的类别（knowledge/goal 交给知识库与计划篇）
INJECTABLE_CATEGORIES = ("preference", "behavior", "context")

# context 类只有在"短 + 高置信"时才值得占提示词预算
CONTEXT_MAX_CHARS = 160
CONTEXT_MIN_CONFIDENCE = 0.8
# 单条上限：再长就不是"事实"，是段落
FACT_MAX_CHARS = 400
# 一次注入最多条数，避免把上下文吃光
DEFAULT_INJECT_LIMIT = 10


def _field(fact: Any, name: str, default: Any = None) -> Any:
    """从对象或字典里取字段，统一注入层的入参形状。"""
    if isinstance(fact, dict):
        return fact.get(name, default)
    return getattr(fact, name, default)


def standing_fact_allowed(fact: Any, *, chat_compact: bool = False) -> bool:
    """逐条判定这条记忆能不能进提示词（原版 ``_standing_fact_allowed`` 主干）。

    保留的 5 条规则：
        1. 空内容 → 丢
        2. 类别不在 preference/behavior/context → 丢（knowledge/goal 不注入）
        3. 单条 > 400 字 → 丢（不是事实）
        4. context 类：>160 字或 confidence < 0.8 → 丢
        5. chat_compact=True 时只保留 preference（压缩态下只带最稳的偏好）
    """
    content = str(_field(fact, "content", "") or "").strip()
    if not content:
        return False
    category = _field(fact, "category")
    confidence = float(_field(fact, "confidence", 0.0) or 0.0)

    if category not in INJECTABLE_CATEGORIES:
        return False
    if len(content) > FACT_MAX_CHARS:
        return False
    if chat_compact and category != "preference":
        return False
    if category == "context":
        return len(content) <= CONTEXT_MAX_CHARS and confidence >= CONTEXT_MIN_CONFIDENCE
    return True


def format_memory_for_injection(
    facts: Iterable[Any],
    *,
    chat_compact: bool = False,
    limit: int = DEFAULT_INJECT_LIMIT,
) -> str:
    """把通过过滤的记忆拼成一段提示词块；没有可用条目返回空字符串。"""
    kept: list[str] = []
    for fact in facts:
        if not standing_fact_allowed(fact, chat_compact=chat_compact):
            continue
        content = getattr(fact, "content", None)
        if content is None and isinstance(fact, dict):
            content = fact.get("content", "")
        category = getattr(fact, "category", None)
        if category is None and isinstance(fact, dict):
            category = fact.get("category", "")
        kept.append(f"- [{category}] {str(content).strip()}")
        if len(kept) >= limit:
            break
    if not kept:
        return ""
    return "以下是已确认的长期记忆（优先于临时推测）：\n" + "\n".join(kept)


def candidates_to_facts(candidates: Iterable[FactCandidate]) -> list[dict[str, object]]:
    """把抽取结果转成注入层接受的最小结构（dict 形态）。"""
    return [candidate.to_dict() for candidate in candidates]


__all__ = [
    "CONTEXT_MAX_CHARS",
    "DEFAULT_INJECT_LIMIT",
    "FACT_MAX_CHARS",
    "INJECTABLE_CATEGORIES",
    "candidates_to_facts",
    "format_memory_for_injection",
    "standing_fact_allowed",
]
