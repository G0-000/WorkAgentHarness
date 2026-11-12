"""工具历史合并（对齐 EvoFlow ``context/tool_history_merge.py``）。

原版符号与行号（快照 8e462a37）：
    ToolRoundEntry        ← :58
    _eligible_cold_tool   ← :108
    _scan_cold_prefix     ← :120
    rebuild_cold_prefix   ← :201
    apply_cold_zone_policy← :266

学习版只做第 14 章需要的最小能力：**同一个文件被读多次，只保留最后一次结果**。
不实现"冷区 + 冷却 + 批量重写"（那是原版面向多用户长会话的策略），
本仓单进程 CLI 场景下，按文件去重已经能解决"一个大文件读三遍吃光预算"。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from langchain_core.messages import BaseMessage, ToolMessage

# 从 AIMessage.tool_calls 的 args 里认这些键，作为"同一资源"的归并键
FILE_ARG_KEYS = ("path", "file_path", "abs_path", "filepath", "target_file")

# 这些工具名本身就带文件语义，args 里没有路径时也能识别
FILE_TOOL_HINTS = ("read_file", "write_file", "edit_file", "list_dir", "read_text")


@dataclass(frozen=True)
class ToolRoundEntry:
    """一条工具结果，连同它的调用参数（对应原版 ``ToolRoundEntry``）。"""

    index: int
    tool_call_id: str
    tool_name: str
    merge_key: str | None

    @property
    def is_mergeable(self) -> bool:
        return self.merge_key is not None


def _tool_call_args(message: BaseMessage) -> dict[str, Any]:
    """从 AI 消息里取出 tool_call 的 args（按 tool_call_id 对齐）。"""
    calls = getattr(message, "tool_calls", None) or []
    return {call.get("id"): call.get("args") or {} for call in calls if isinstance(call, dict)}


def _file_path_from_args(args: dict[str, Any]) -> str | None:
    for key in FILE_ARG_KEYS:
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def build_tool_round_entries(messages: Iterable[BaseMessage]) -> list[ToolRoundEntry]:
    """扫描整段消息，给每条 ToolMessage 标注归并键。

    归并键优先级：
        1) 同一次 tool_call 的 args 里能认出文件路径 → ``file:<path>``
        2) ToolMessage.additional_kwargs 里显式写了 ``merge_key`` → 原样使用
        3) 其余 → None（不参与合并）
    """
    call_args: dict[Any, dict[str, Any]] = {}
    entries: list[ToolRoundEntry] = []
    for index, message in enumerate(list(messages)):
        if not isinstance(message, ToolMessage):
            call_args.update(_tool_call_args(message))
            continue
        tool_call_id = getattr(message, "tool_call_id", "") or f"idx{index}"
        args = call_args.get(getattr(message, "tool_call_id", None), {})
        path = _file_path_from_args(args)
        explicit = (getattr(message, "additional_kwargs", {}) or {}).get("merge_key")
        if path:
            merge_key = f"file:{path}"
        elif isinstance(explicit, str) and explicit.strip():
            merge_key = explicit.strip()
        else:
            merge_key = None
        entries.append(
            ToolRoundEntry(
                index=index,
                tool_call_id=tool_call_id,
                tool_name=getattr(message, "name", "") or "",
                merge_key=merge_key,
            )
        )
    return entries


def plan_tool_history_merge(
    messages: Iterable[BaseMessage], *, preserve_ids: frozenset[str] = frozenset()
) -> tuple[list[str], int]:
    """计算"哪些 ToolMessage 该被丢掉"，返回 (消息 id 列表, 合并条数)。

    只按位置丢弃，不修改保留内容：调用方拿到 id 后用 ``RemoveMessage`` 删除。
    ``preserve_ids`` 命中的消息永不淘汰（用于用户显式要求保留的工具结果）。
    """
    materialized = list(messages)
    entries = build_tool_round_entries(materialized)
    by_key: dict[str, list[ToolRoundEntry]] = {}
    for entry in entries:
        if entry.merge_key:
            by_key.setdefault(entry.merge_key, []).append(entry)

    drop: list[str] = []
    merged = 0
    for key, group in by_key.items():
        if len(group) < 2:
            continue
        # 保留最后一次（最新一次的读取结果才是当前事实）
        for entry in group[:-1]:
            message = materialized[entry.index]
            message_id = getattr(message, "id", None)
            if not message_id or entry.tool_call_id in preserve_ids or message_id in preserve_ids:
                continue
            if getattr(message, "name", "") not in FILE_TOOL_HINTS and not getattr(
                message, "additional_kwargs", {}
            ).get("merge_key"):
                continue
            drop.append(message_id)
            merged += 1
    return drop, merged


__all__ = [
    "FILE_ARG_KEYS",
    "ToolRoundEntry",
    "build_tool_round_entries",
    "plan_tool_history_merge",
]
