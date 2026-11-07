"""宿主终端工具（对齐 EvoFlow ``tools/host_direct/terminal_tool.py`` 的简化版）。

原版对应关系（逐条可查）：
    _DANGEROUS_PATTERNS   ← terminal_tool.py:506
    _check_dangerous      ← terminal_tool.py:553
    _run_subprocess       ← terminal_tool.py:173
    _format_subprocess_output ← terminal_tool.py:129
    _spawn_background     ← terminal_tool.py:438
    _should_auto_background ← terminal_tool.py:518
    _foreground_timeout   ← terminal_tool.py:524
    terminal_tool         ← terminal_tool.py:567

与原版的差异（台账已登记）：
    1. 不实现 PTY（``_run_via_pty``），学习版只跑一次性命令。
    2. 不接 exploration budget（``check_tool_budget``），学习版没有该模块。
    3. 拦下危险命令时，在原版警告文本前加 ``[DangerousCommand]`` 前缀，
       以便本项目的事件层（``events/stream.py`` 按 ``[`` 判失败）能正确判 ok。
"""

from __future__ import annotations

import os
import re
import subprocess
import time
import uuid
from pathlib import Path

from langchain_core.tools import tool

_DEFAULT_TIMEOUT = 30
_FOREGROUND_MAX_TIMEOUT = 120
_MAX_OUTPUT_CHARS = 8000
_LOG_DIR = Path("data/term_logs")

# ── 危险命令模式（原版 terminal_tool.py:506 的 8 条，逐条附说明）───────────
# 每条是 (正则, 危险类别 id)。命中即拒绝执行，除非用户加 "force:" 前缀。
_DANGEROUS_PATTERNS: list[tuple[re.Pattern, str]] = [
    # 删除根目录 / 当前目录 / 通配符全删：最典型的误操作
    (
        re.compile(r"^\s*(rm|rmdir|del|deltree|rd)\s+(-rf?\s+)?/?(\*|\.\s*$|/|\\[\\/]?\s*$)"),
        "destructive_root",
    ),
    # 格式化 / 分区 / 裸写磁盘
    (re.compile(r"^\s*(mkfs|fdisk|dd|format)\s"), "destructive_disk"),
    # 把根目录权限放开给所有人
    (re.compile(r"^\s*chmod\s+-R?\s*777\s+/"), "permission_risk"),
    # 立即关机 / 重启
    (re.compile(r"^\s*shutdown\s+-[rh]?\s*(now|\+0)"), "system_shutdown"),
    (re.compile(r"^\s*reboot\s*$"), "system_reboot"),
    # 提权后删除：比普通删除更危险
    (re.compile(r"^\s*sudo\s+rm\s+-rf\s+/"), "sudo_destructive"),
    # 直接覆盖磁盘设备
    (re.compile(r"^\s*>\s*/dev/sd"), "disk_overwrite"),
    # 下载脚本直接管道给 shell 执行：远程代码执行
    (re.compile(r"^\s*curl\s+[^\s]+\s*\|\s*(bash|sh|zsh|python)"), "pipe_curl_to_shell"),
]

# 看起来像长时间任务、应转后台的模式（原版 _AUTO_BACKGROUND_PATTERNS 的精简）
_AUTO_BACKGROUND_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bnpm\s+(install|ci)\b", re.I),
    re.compile(r"\bpnpm\s+(install|i)\b", re.I),
    re.compile(r"\bpytest\b|\btox\b", re.I),
    re.compile(r"\buvicorn\b|\bgunicorn\b|\bvite\b|\bnext\s+dev\b", re.I),
    re.compile(r"\btail\s+-f\b|\bwatch\b", re.I),
]

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    """去掉终端颜色控制符（原版 terminal_tool.py:123）。"""
    return _ANSI_ESCAPE.sub("", text or "")


def _format_subprocess_output(stdout: str, stderr: str, exit_code: int) -> str:
    """把 stdout / stderr / exit code 拼成模型可读的一段文本（原版 :129）。"""
    parts: list[str] = []
    body = _strip_ansi((stdout or "").rstrip())
    err = _strip_ansi((stderr or "").rstrip())
    if body:
        parts.append(body)
    if err:
        # stderr 单独标注，避免模型把报错当成正常输出
        parts.append(f"[stderr]\n{err}")
    if exit_code != 0:
        parts.append(f"[exit_code={exit_code}]")
    text = "\n".join(parts) if parts else "(无输出)"
    if len(text) > _MAX_OUTPUT_CHARS:
        # 只留头部和尾部：中间通常是重复日志，头尾更有信息量
        head = text[: _MAX_OUTPUT_CHARS // 2]
        tail = text[-_MAX_OUTPUT_CHARS // 2 :]
        return f"{head}\n…（输出过长，已截断，共 {len(text)} 字符）…\n{tail}"
    return text


def _run_subprocess(command: str, cwd: Path | None, timeout: int) -> tuple[str, int]:
    """前台执行一条命令，返回 (格式化输出, exit_code)（原版 :173 的简化）。"""
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        # 超时不抛异常给模型，转成可读结果：告诉它超了多少秒、怎么做
        waited = round(time.monotonic() - started, 1)
        out = _format_subprocess_output(
            (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            (exc.stderr or "") if isinstance(exc.stderr, str) else "",
            124,
        )
        return f"{out}\n[Timeout] 前台等待 {waited}s 后结束（上限 {timeout}s），长任务请用 background=True", 124
    return _format_subprocess_output(proc.stdout, proc.stderr, proc.returncode), proc.returncode


def _foreground_timeout(command: str, timeout: int, *, explicit_timeout: bool) -> int:
    """前台等待上限（原版 :524）：至少 1 秒，最多 _FOREGROUND_MAX_TIMEOUT。"""
    del command, explicit_timeout  # 原版按 curl 探测放宽，学习版不需要
    return min(max(1, int(timeout)), _FOREGROUND_MAX_TIMEOUT)


def _should_auto_background(command: str, background: bool) -> bool:
    """判断是否该自动转后台（原版 :518）。"""
    if background:
        return False
    return any(p.search(command) for p in _AUTO_BACKGROUND_PATTERNS)


def _spawn_background(command: str, cwd: Path | None) -> tuple[str, Path]:
    """后台启动命令，返回 (pid, 日志路径)（原版 :438 的简化）。

    做法：nohup + 重定向到日志文件，父进程立刻返回 pid。
    """
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = _LOG_DIR / f"{uuid.uuid4().hex[:8]}.log"
    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        command,
        shell=True,
        cwd=str(cwd) if cwd else None,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,  # 脱离当前进程组，父进程退出后仍继续
    )
    return str(proc.pid), log_path


def _check_dangerous(command: str) -> str | None:
    """命中危险模式返回警告文本，否则返回 None（原版 :553）。"""
    for pattern, danger_id in _DANGEROUS_PATTERNS:
        if pattern.search(command):
            return (
                f"[DangerousCommand] safety guard ({danger_id}):\n{command[:200]}\n\n"
                "确认要执行时，在原命令前加 'force:' 再调用一次。"
            )
    return None


def _resolve_cwd(workdir: str | None) -> Path | None:
    """把 workdir 解析成绝对路径；空值返回 None（用当前目录）。"""
    if not workdir:
        return None
    target = Path(workdir).expanduser()
    return target if target.is_absolute() else Path.cwd() / target


@tool("terminal", parse_docstring=False)
def terminal_tool(
    command: str,
    background: bool = False,
    timeout: int | None = None,
    workdir: str | None = None,
) -> str:
    """Execute a shell command on the host. 长任务用 background=True。"""
    # ── 第一步：force: 前缀是"用户已确认"的显式信号 ────────────────────
    effective_command = command
    force_mode = False
    if command.startswith("force:"):
        effective_command = command[len("force:") :].lstrip()
        force_mode = True

    # ── 第二步：未确认先过安全护栏，命中直接返回警告（不执行）──────────
    if not force_mode:
        warning = _check_dangerous(effective_command)
        if warning:
            return warning

    cwd = _resolve_cwd(workdir)

    # ── 第三步：长任务转后台，立刻返回 pid 和日志路径 ───────────────────
    if background or _should_auto_background(effective_command, background):
        pid, log_path = _spawn_background(effective_command, cwd)
        return f"[Background] pid={pid}\nlog={log_path}\n查看输出请读该日志文件。"

    # ── 第四步：前台执行，超时按上限截断 ────────────────────────────────
    wait = _foreground_timeout(
        effective_command,
        timeout if timeout is not None else _DEFAULT_TIMEOUT,
        explicit_timeout=timeout is not None,
    )
    output, exit_code = _run_subprocess(effective_command, cwd, wait)
    return output if output else f"(exit_code={exit_code})"


__all__ = [
    "terminal_tool",
    "_check_dangerous",
    "_run_subprocess",
    "_spawn_background",
    "_should_auto_background",
    "_format_subprocess_output",
]
