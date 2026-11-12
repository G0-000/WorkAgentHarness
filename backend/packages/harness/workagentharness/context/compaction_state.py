"""折叠状态：pinned 标记 + 折叠记录（第 14 章 WAH-MEM-008）。

原版把"折了几条、折完模型看到哪一版"存在中间件私有状态里，通过
``compaction_fold_msg_counts()``（:93）与 ``last_bound_model_messages()``（:97）回读。
学习版把同样的信息结构化成 ``FoldRecord``，并加一条 ``pinned`` 约定：
被用户钉住的消息（命名规范、已改文件路径）折叠时跳过。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable

from langchain_core.messages import BaseMessage

# 钉住标记写在哪：additional_kwargs["pinned"] = True
PIN_KEY = "pinned"

# 只保留最近 50 次折叠记录，避免长会话无限增长
_FOLD_HISTORY: deque["FoldRecord"] = deque(maxlen=50)


@dataclass(frozen=True)
class FoldRecord:
    """一次折叠的可观测结果（对应用户问题"为什么少了两条"）。"""

    before: int
    after: int
    folded: int
    merged_tool_messages: int = 0
    pinned_kept: int = 0
    total_tokens: int = 0
    estimator: str = "chars//3"
    folded_ids: tuple[str, ...] = field(default=())

    def to_meta(self) -> dict[str, Any]:
        return {
            "before": self.before,
            "after": self.after,
            "folded": self.folded,
            "merged_tool_messages": self.merged_tool_messages,
            "pinned_kept": self.pinned_kept,
            "total_tokens": self.total_tokens,
            "estimator": self.estimator,
        }


def is_pinned(message: Any) -> bool:
    """消息是否被钉住（显式规范、已改文件路径这类不许折的内容）。"""
    kwargs = getattr(message, "additional_kwargs", {}) or {}
    return bool(kwargs.get(PIN_KEY))


def pin_message(message: Any, *, reason: str = "") -> None:
    """就地给消息打钉（LangChain 消息的 additional_kwargs 是可写 dict）。"""
    kwargs = getattr(message, "additional_kwargs", None)
    if isinstance(kwargs, dict):
        kwargs[PIN_KEY] = True
        if reason:
            kwargs["pinned_reason"] = reason


def split_pinned(messages: Iterable[BaseMessage]) -> tuple[list[BaseMessage], list[BaseMessage]]:
    """把一段消息拆成 (被钉住的, 未钉住的)，保持各自原始顺序。"""
    pinned: list[BaseMessage] = []
    rest: list[BaseMessage] = []
    for message in messages:
        (pinned if is_pinned(message) else rest).append(message)
    return pinned, rest


def record_fold(
    *,
    before: int,
    after: int,
    merged_tool_messages: int = 0,
    pinned_kept: int = 0,
    total_tokens: int = 0,
    estimator: str = "chars//3",
    folded_ids: Iterable[str] = (),
) -> FoldRecord:
    """写入一条折叠记录，返回该记录（同时进入最近 50 条历史）。"""
    record = FoldRecord(
        before=before,
        after=after,
        folded=max(0, before - after),
        merged_tool_messages=merged_tool_messages,
        pinned_kept=pinned_kept,
        total_tokens=total_tokens,
        estimator=estimator,
        folded_ids=tuple(folded_ids),
    )
    _FOLD_HISTORY.append(record)
    return record


def last_fold_record() -> FoldRecord | None:
    """最近一次折叠记录；没折过返回 None。"""
    return _FOLD_HISTORY[-1] if _FOLD_HISTORY else None


def fold_history() -> list[FoldRecord]:
    """全部折叠历史（最多 50 条），按发生顺序。"""
    return list(_FOLD_HISTORY)


def reset_fold_records() -> None:
    """清空历史，供测试与"新会话"场景复位。"""
    _FOLD_HISTORY.clear()


__all__ = [
    "FoldRecord",
    "PIN_KEY",
    "fold_history",
    "is_pinned",
    "last_fold_record",
    "pin_message",
    "record_fold",
    "reset_fold_records",
    "split_pinned",
]
