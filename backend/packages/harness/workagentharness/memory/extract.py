"""记忆巩固：从对话里抽取事实（对齐 EvoFlow ``agents/memory/prompt.py`` / ``updater.py``）。

原版符号（快照 8e462a37）：
    FACT_EXTRACTION_PROMPT         ← agents/memory/prompt.py:145
    MEMORY_UPDATE_PROMPT           ← prompt.py:15
    format_conversation_for_update ← prompt.py:384

本项目偏差（有意）：
    原版让模型按提示词输出 JSON；本仓 ``provider: fake``，离线条件下改用**句式规则**抽取，
    输出形状与 ``FACT_EXTRACTION_PROMPT`` 一致：``content`` + ``category`` + ``confidence``。
"""

from __future__ import annotations

from dataclasses import dataclass

# 五类分类里，本项目只把这三类当"可进长期"的候选
EXTRACTABLE_CATEGORIES = ("preference", "behavior", "context")

# 明确偏好句式：命中即 1.0
STRONG_PREFERENCE_MARKERS = ("必须", "不要", "一律", "统一", "以后都", "永远")
# 弱偏好句式：命中 0.8
WEAK_PREFERENCE_MARKERS = ("以后", "尽量", "最好", "习惯用")
# 含糊词：置信度降到 0.6
HEDGE_MARKERS = ("可能", "大概", "也许", "应该")
# 一次性指令：只进短期，不进长期
CONTEXT_MARKERS = ("这次", "先别", "暂时", "本次")
# 知识类：交给第五篇知识库，不进记忆
KNOWLEDGE_MARKERS = ("是什么", "原理", "介绍", "怎么实现", "文档")


@dataclass(frozen=True)
class FactCandidate:
    """一条抽取结果，形状对齐 ``FACT_EXTRACTION_PROMPT`` 的 JSON。"""

    content: str
    category: str
    confidence: float

    def to_dict(self) -> dict[str, object]:
        return {"content": self.content, "category": self.category, "confidence": self.confidence}


def _clip(text: str, limit: int = 200) -> str:
    return text.strip().replace("\n", " ")[:limit]


def extract_facts(text: str) -> list[FactCandidate]:
    """按句式规则抽取；抽不出返回空列表（不会硬造一条）。"""
    raw = (text or "").strip()
    if not raw:
        return []
    clipped = _clip(raw)

    # 知识类优先排除：问原理/介绍文档，不是偏好
    if any(marker in clipped for marker in KNOWLEDGE_MARKERS):
        return []

    # 一次性指令：进短期上下文，置信度 0.8（长度还要在注入时二次过滤）
    if any(marker in clipped for marker in CONTEXT_MARKERS):
        return [FactCandidate(content=clipped, category="context", confidence=0.8)]

    confidence = 0.8
    if any(marker in clipped for marker in HEDGE_MARKERS):
        confidence = 0.6
    elif any(marker in clipped for marker in STRONG_PREFERENCE_MARKERS):
        confidence = 1.0

    if any(marker in clipped for marker in STRONG_PREFERENCE_MARKERS + WEAK_PREFERENCE_MARKERS):
        return [FactCandidate(content=clipped, category="preference", confidence=confidence)]

    # 行为约定："每次/总是 + 动作"
    if "每次" in clipped or "总是" in clipped:
        return [FactCandidate(content=clipped, category="behavior", confidence=confidence)]

    return []


def should_persist_long_term(candidate: FactCandidate) -> bool:
    """准入：只有 preference/behavior，且 confidence ≥ 0.8 才进长期。

    "这次先别看 tests" 这类 context 一律留在短期——这是本章的核心边界。
    """
    return candidate.category in ("preference", "behavior") and candidate.confidence >= 0.8


__all__ = [
    "EXTRACTABLE_CATEGORIES",
    "FactCandidate",
    "extract_facts",
    "should_persist_long_term",
]
