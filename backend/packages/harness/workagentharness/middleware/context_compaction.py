"""上下文折叠中间件（对齐 EvoFlow ``agents/middlewares/context_compaction_middleware.py``）。

原版对应符号：
    compaction_folded_this_call   ← context_compaction_middleware.py:89
    compaction_fold_msg_counts    ← :93
    last_bound_model_messages     ← :97
    mark_skip_compaction_once     ← :103
    consume_skip_compaction_once  ← :108

第 14 章在第三篇的字符阈值折叠上补了三件事（WAH-MEM-001 / 008 / TOOL-007）：
    1. token 估算（``context/token_budget.py``），折叠前后都写进记录；
    2. pinned 消息不折叠（``context/compaction_state.py``）；
    3. 同一文件的重复 ToolMessage 只留最后一次（``context/tool_history_merge.py``）。

机制差异（台账已登记）：
    原版是"预算驱动 + 异步队列 + 模型摘要"；学习版是"字符阈值 + 同步折叠 + 本地摘要"，
    保证离线可验证。原版没有名为 ``ContextBudgetMiddleware`` 的类。
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage, RemoveMessage

from workagentharness.context.compaction_state import (
    FoldRecord,
    last_fold_record,
    record_fold,
    split_pinned,
)
from workagentharness.context.token_budget import TokenEstimate, estimate_request_tokens
from workagentharness.context.tool_history_merge import plan_tool_history_merge

# 触发折叠的字符阈值：超过就把早期消息折成一段摘要
MAX_CONTEXT_CHARS = 12000
# 保留最近 N 条原始消息（对话的"当下语境"不能丢）
KEEP_RECENT_MESSAGES = 6

# 单次调用内的折叠结果：(折叠前条数, 折叠后条数)
_fold_counts: ContextVar[tuple[int, int] | None] = ContextVar("fold_counts", default=None)
# 一次性跳过标记：某些轮次不希望被折叠打断（如工具结果刚回来）
_skip_once: ContextVar[bool] = ContextVar("skip_compaction_once", default=False)
# 折叠后模型实际收到的这一版的 token 估算（对应原版 last_bound_model_messages）
_last_bound: ContextVar[TokenEstimate | None] = ContextVar("last_bound_estimate", default=None)


def compaction_folded_this_call() -> bool:
    """本次模型调用是否发生了折叠（原版 :89）。"""
    return _fold_counts.get() is not None


def compaction_fold_msg_counts() -> tuple[int, int] | None:
    """返回 (折叠前, 折叠后) 消息条数，便于日志与 UI 展示（原版 :93）。"""
    return _fold_counts.get()


def compaction_last_bound_estimate() -> TokenEstimate | None:
    """折叠后"模型实际收到的那一版"的 token 估算（原版 :97 的学习版口径）。"""
    return _last_bound.get()


def compaction_fold_detail() -> FoldRecord | None:
    """最近一次折叠的完整记录：折了几条、合并了几条工具结果、钉住几条。"""
    return last_fold_record()


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
    """字符数：折叠的触发口径（token 估算只用于记录，不参与触发）。"""
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

        # 被钉住的消息（命名规范、已改文件路径）不参与折叠，原样留在上下文里
        pinned, foldable = split_pinned(head)

        # 同一文件的重复读取只留最后一次：先从摘要输入里剔除，再删消息
        merge_drop_ids, merged_tools = plan_tool_history_merge(foldable)
        summarized = [m for m in foldable if getattr(m, "id", "") not in merge_drop_ids]

        # 用 RemoveMessage 删掉旧消息，再插入一条摘要消息；
        # 直接返回新列表会被 add_messages reducer 追加，而不是替换。
        removals = [RemoveMessage(id=getattr(m, "id", "")) for m in foldable if getattr(m, "id", None)]
        summary = HumanMessage(content=_fold_summary(summarized), name="context_summary")

        bound = pinned + [summary] + recent
        estimate = estimate_request_tokens(bound)
        _last_bound.set(estimate)

        _fold_counts.set((len(messages), len(bound)))
        record_fold(
            before=len(messages),
            after=len(bound),
            merged_tool_messages=merged_tools,
            pinned_kept=len(pinned),
            total_tokens=estimate.total_tokens,
            estimator=estimate.estimator,
            folded_ids=[getattr(m, "id", "") for m in foldable if getattr(m, "id", "") and getattr(m, "id", "") not in merge_drop_ids],
        )
        return {"messages": removals + [summary]}


__all__ = [
    "ContextCompactionMiddleware",
    "MAX_CONTEXT_CHARS",
    "KEEP_RECENT_MESSAGES",
    "compaction_folded_this_call",
    "compaction_fold_msg_counts",
    "compaction_last_bound_estimate",
    "compaction_fold_detail",
    "mark_skip_compaction_once",
    "consume_skip_compaction_once",
]
