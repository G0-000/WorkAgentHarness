"""上下文折叠中间件（对齐 EvoFlow ``agents/middlewares/context_compaction_middleware.py``）。

原版对应符号：
    compaction_folded_this_call   ← context_compaction_middleware.py:89
    compaction_fold_msg_counts    ← :93
    mark_skip_compaction_once     ← :103
    consume_skip_compaction_once  ← :108

机制差异（台账已登记）：
    原版把旧消息**折叠**成摘要后继续对话（fold），并在需要时跳过一轮压缩；
    学习版用同一套"折叠"思路，但摘要由本地规则生成（截取每条消息首行拼装），
    不调用模型，保证离线可验证。原版没有名为 ``ContextBudgetMiddleware`` 的类。
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage, RemoveMessage

# 触发折叠的字符阈值：超过就把早期消息折成一段摘要
MAX_CONTEXT_CHARS = 12000
# 保留最近 N 条原始消息（对话的"当下语境"不能丢）
KEEP_RECENT_MESSAGES = 6

# 单次调用内的折叠结果：(折叠前条数, 折叠后条数)
_fold_counts: ContextVar[tuple[int, int] | None] = ContextVar("fold_counts", default=None)
# 一次性跳过标记：某些轮次不希望被折叠打断（如工具结果刚回来）
_skip_once: ContextVar[bool] = ContextVar("skip_compaction_once", default=False)


def compaction_folded_this_call() -> bool:
    """本次模型调用是否发生了折叠（原版 :89）。"""
    return _fold_counts.get() is not None


def compaction_fold_msg_counts() -> tuple[int, int] | None:
    """返回 (折叠前, 折叠后) 消息条数，便于日志与 UI 展示（原版 :93）。"""
    return _fold_counts.get()


def mark_skip_compaction_once() -> None:
    """标记下一轮跳过折叠（原版 :103）。"""
    _skip_once.set(True)


def consume_skip_compaction_once() -> bool:
    """读取并清除跳过标记，保证只生效一次（原版 :108）。"""
    if _skip_once.get():
        _skip_once.set(False)
        return True
    return False


def _message_text(message: Any) -> str:
    """把消息内容压成一行文本，用于生成摘要。"""
    content = getattr(message, "content", "")
    if isinstance(content, list):
        content = " ".join(str(part) for part in content)
    text = str(content or "").strip().replace("\n", " ")
    return text[:160]


def _fold_summary(messages: list[Any]) -> str:
    """把被折叠的消息压成一段摘要（本地规则，不调模型）。"""
    lines = []
    for message in messages:
        role = getattr(message, "type", "message")
        text = _message_text(message)
        if text:
            lines.append(f"- {role}: {text}")
    return "（以下为已折叠的历史，仅保留要点）\n" + "\n".join(lines)


def _total_chars(messages: list[Any]) -> int:
    """估算上下文长度：字符数比 token 数更好算，学习版用它做阈值判断。"""
    return sum(len(str(getattr(m, "content", "") or "")) for m in messages)


class ContextCompactionMiddleware(AgentMiddleware):
    """在模型调用前折叠过长的历史消息。

    为什么放在 before_model：
        折叠必须在"消息要发给模型"之前完成；放在 after_model 只能影响下一轮，
        而本轮可能已经因为超长被截断。
    """

    def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        # 一次性跳过：例如工具结果刚回来那一轮，折叠会打断因果关系
        if consume_skip_compaction_once():
            return None

        messages = list(state.get("messages", []) if isinstance(state, dict) else [])
        if _total_chars(messages) <= MAX_CONTEXT_CHARS:
            return None

        if len(messages) <= KEEP_RECENT_MESSAGES:
            # 条数已经很少，再折叠会丢光上下文，直接放过
            return None

        head = messages[:-KEEP_RECENT_MESSAGES]
        recent = messages[-KEEP_RECENT_MESSAGES:]

        # 用 RemoveMessage 删掉旧消息，再插入一条摘要消息；
        # 直接返回新列表会被 add_messages reducer 追加，而不是替换。
        removals = [RemoveMessage(id=getattr(m, "id", "")) for m in head if getattr(m, "id", None)]
        summary = HumanMessage(content=_fold_summary(head), name="context_summary")

        _fold_counts.set((len(messages), len(recent) + 1))
        return {"messages": removals + [summary]}


__all__ = [
    "ContextCompactionMiddleware",
    "MAX_CONTEXT_CHARS",
    "KEEP_RECENT_MESSAGES",
    "compaction_folded_this_call",
    "compaction_fold_msg_counts",
    "mark_skip_compaction_once",
    "consume_skip_compaction_once",
]
