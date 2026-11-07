"""终端会话状态（对齐 EvoFlow ``tools/host_direct/terminal_session.py`` 的简化版）。

原版对应：
    runtime_thread_id     ← terminal_session.py:53
    _flatten_command      ← terminal_session.py:87
    class ThreadShellState ← terminal_session.py:109
    _parse_marked_output  ← terminal_session.py:134

差异：
    原版按 shell 类型（powershell / cmd / bash）做字面量转义并维护线程级 shell；
    学习版只支持 POSIX shell，状态只记 cwd / env / 最近命令。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_MARKER_RE = re.compile(r"__WAH_EXIT__:(-?\d+)")


def runtime_thread_id(runtime: Any) -> str:
    """从 runtime 里取 thread_id（原版 :53）；取不到返回空串。"""
    context = getattr(runtime, "context", None) if runtime is not None else None
    if not context:
        return ""
    try:
        return str(context.get("thread_id") or "").strip()
    except AttributeError:
        return ""


@dataclass
class ThreadShellState:
    """一个 thread 的终端状态（原版 :109 的简化）。

    字段：
        cwd:     当前工作目录，跨多次命令保持
        env:     环境变量覆盖（只记录差异，不复制全环境）
        history: 最近执行的命令，便于排查"为什么 cwd 变了"
    """

    cwd: Path = field(default_factory=Path.cwd)
    env: dict[str, str] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)

    def touch(self, command: str, *, cwd: Path | None = None) -> None:
        """记录一次执行（原版 :118 的 touch）。"""
        if cwd is not None:
            self.cwd = cwd
        self.history.append(command)
        # 只保留最近 50 条，避免长会话无限增长
        del self.history[:-50]


def _flatten_command(command: str, *, state: ThreadShellState) -> str:
    """把会话状态（cwd）拼进命令，保证跨命令目录不丢（原版 :87 的简化）。"""
    if not state.cwd:
        return command
    quoted = str(state.cwd).replace("'", "'\\''")
    return f"cd '{quoted}' && {command}"


def _parse_marked_output(raw: str, marker: str = "__WAH_EXIT__") -> tuple[str, int, str | None]:
    """从带标记的输出里拆出 (正文, exit_code, 错误)（原版 :134 的简化）。

    约定：命令末尾追加 ``; echo "__WAH_EXIT__:$?"``，
    这样即使输出被后台缓冲截断，退出码也能单独取到。
    """
    match = _MARKER_RE.search(raw or "")
    if not match:
        return (raw or "").strip(), 0, "未找到退出码标记"
    exit_code = int(match.group(1))
    body = (raw or "")[: match.start()].rstrip()
    return body, exit_code, None


__all__ = [
    "ThreadShellState",
    "runtime_thread_id",
    "_flatten_command",
    "_parse_marked_output",
]
