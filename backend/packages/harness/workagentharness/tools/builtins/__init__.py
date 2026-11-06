"""内置工具集合。

新增内置工具的步骤：
    1. 在本目录写一个 ``@tool`` 函数（返回值保持字符串或 ToolResult 文本）
    2. 在 ``default_catalog()`` 里注册，并给别名和 tier
    3. 在文档 doc/code/tools/builtins/ 下补对应说明
"""

from __future__ import annotations

from ..catalog import ToolCatalog
from .calculator import calculator, safe_eval
from .workspace_file import list_directory, read_text_file, resolve_in_workspace

__all__ = [
    "calculator",
    "safe_eval",
    "read_text_file",
    "list_directory",
    "resolve_in_workspace",
    "default_catalog",
]


def default_catalog() -> ToolCatalog:
    """构造默认工具目录：当前只含计算与只读文件两类工具。

    为什么先只放这两个：
        计算工具无副作用，最适合验证"模型发起调用 → 工具执行 → 结果回传"闭环；
        文件工具只读 + 边界校验，用来演示"宿主边界"而在本篇不引入写操作风险。
    """
    catalog = ToolCatalog()
    catalog.register(calculator, tier="core", aliases=("calc", "math"))
    catalog.register(read_text_file, tier="workspace", aliases=("read_file",))
    catalog.register(list_directory, tier="workspace", aliases=("ls",))
    return catalog
