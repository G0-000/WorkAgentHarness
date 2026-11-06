"""工具结果的标准协议。

所有工具最终都把返回值收敛成同一种形状（ToolResult），
这样 Agent、UI、日志、事件流都只需要处理一种结果类型，
不用关心具体工具是返回字符串、字典还是对象。

对应 EvoFlow 的 ``tools/tool_result_shaper.py`` + ``tools/tool_output_truncation.py``
的简化版：不做分字段整形，只做"统一结构 + 大结果截断"。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 单次工具结果进入上下文的最大字符数；超出部分截断并在 metadata 标记。
MAX_RESULT_CHARS = 8000


@dataclass(frozen=True)
class ToolResult:
    """一次工具调用的结构化结果。

    字段说明：
        ok:         是否成功
        content:    给模型看的文本（已截断）
        error_code: 失败时的稳定错误类别（如 InvalidArgs / Timeout），不含异常原文
        truncated:  内容是否被截断
        metadata:   结构化附加信息（如行数、字节数、耗时）
    """

    ok: bool
    content: str
    error_code: str = ""
    truncated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def truncate_text(text: str, limit: int = MAX_RESULT_CHARS) -> tuple[str, bool]:
    """把过长文本截断到 limit 字符，返回 (截断后文本, 是否发生截断)。

    截断时保留头部，并在末尾注明总长度，让模型知道后面还有内容
    （后续可用大结果引用再取，见 WAH-TOOL-教材中的 large result 思路）。
    """
    if text is None:
        return "", False
    if len(text) <= limit:
        return text, False
    head = text[:limit]
    return f"{head}\n…（已截断，原文共 {len(text)} 字符）", True


def shape_result(
    tool_name: str,
    ok: bool,
    content: str,
    *,
    error_code: str = "",
    metadata: dict[str, Any] | None = None,
) -> ToolResult:
    """把任意工具输出收敛成 ToolResult。

    所有内置工具都通过这里返回，保证错误类别、截断、元信息一致。
    """
    body, truncated = truncate_text(content)
    meta = {"tool": tool_name}
    if metadata:
        meta.update(metadata)
    return ToolResult(
        ok=ok,
        content=body,
        error_code=error_code,
        truncated=truncated,
        metadata=meta,
    )
