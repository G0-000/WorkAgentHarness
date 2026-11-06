"""工具层对外出口。

三个子模块对应第三篇第 6–7 章：
    - result.py    工具结果标准协议（WAH-TOOL-002）
    - catalog.py   工具目录、别名与 schema（WAH-TOOL-001）
    - builtins/    内置计算与文件工具（WAH-TOOL-003/004 的最小实现）
"""

from .catalog import ToolCatalog, ToolEntry
from .result import MAX_RESULT_CHARS, ToolResult, shape_result, truncate_text

__all__ = [
    "ToolCatalog",
    "ToolEntry",
    "ToolResult",
    "shape_result",
    "truncate_text",
    "MAX_RESULT_CHARS",
]
