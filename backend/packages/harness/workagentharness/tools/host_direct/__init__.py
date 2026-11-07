"""宿主直连工具（对齐 EvoFlow ``tools/host_direct/`` 的简化版）。

原版这个目录下有 terminal_tool / terminal_session / read_file / write_file 等；
学习版只实现终端一块（第三篇 8.1），其余仍是 ``tools/builtins/workspace_file.py`` 的只读能力。
"""

from __future__ import annotations

from .terminal_tool import terminal_tool
from .terminal_session import ThreadShellState, runtime_thread_id, _flatten_command, _parse_marked_output

__all__ = [
    "terminal_tool",
    "ThreadShellState",
    "runtime_thread_id",
    "_flatten_command",
    "_parse_marked_output",
]
