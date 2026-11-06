"""内置文件工具：读文件 / 列目录（仅限工作区根目录内）。

对应第三篇"文件/终端/宿主边界"的最小实现（WAH-TOOL-003）：
    工具跑在"宿主"上，能碰真实文件系统，因此必须先划定边界——
    只允许读 ``WORKAGENT_WORKSPACE`` 根目录下的文件，拒绝绝对路径和 ``..``。

宿主边界的含义（本篇最重要的认知）：
    模型能决定"读哪个文件"，但边界由宿主代码强制，
    不能靠提示词约束，也不能靠"模型不会乱来"。

终端执行（shell）本篇不做：它属于 WAH-TOOL-010/011 的高危面，
需要命令白名单 + 超时 + 输出上限 + 审批，留到第 8 章讨论。
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_core.tools import tool

from ..result import shape_result


def workspace_root() -> Path:
    """工作区根：优先读环境变量，缺省用当前进程的工作目录。"""
    raw = os.environ.get("WORKAGENT_WORKSPACE", "").strip()
    return Path(raw).expanduser().resolve() if raw else Path.cwd().resolve()


def resolve_in_workspace(path: str) -> Path:
    """把用户给定的相对路径解析成工作区内的绝对路径；越界一律 ValueError。"""
    if not path or not path.strip():
        raise ValueError("路径不能为空")
    candidate = Path(path.strip())
    if candidate.is_absolute():
        # 绝对路径直接拒绝：工具只认相对路径，避免模型拼出 /etc/passwd
        raise ValueError("不允许绝对路径，请使用工作区内的相对路径")
    root = workspace_root()
    target = (root / candidate).resolve()
    # 解析后必须仍在 root 下（这一步能挡住 ../ 逃逸和符号链接逃逸）
    if root not in target.parents and target != root:
        raise ValueError("路径越出工作区范围")
    return target


@tool
def read_text_file(path: str) -> str:
    """读取工作区内一个文本文件的内容（相对路径，例如 "backend/config.yaml"）。"""
    try:
        target = resolve_in_workspace(path)
    except ValueError as exc:
        return f"[PathNotAllowed] {exc}"
    if not target.exists():
        return "[NotFound] 文件不存在"
    if not target.is_file():
        return "[NotAFile] 目标不是文件"
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # 二进制文件不给模型硬读，避免上下文里塞乱码
        return "[NotText] 不是 UTF-8 文本文件"
    except OSError as exc:
        return f"[ReadError] {type(exc).__name__}"
    # 截断逻辑在 ToolResult 里统一做；这里直接返回字符串给工具层
    shaped = shape_result("read_text_file", ok=True, content=text)
    return shaped.content


@tool
def list_directory(path: str = ".") -> str:
    """列出工作区内某个目录下的文件和子目录（相对路径，默认当前目录）。"""
    try:
        target = resolve_in_workspace(path or ".")
    except ValueError as exc:
        return f"[PathNotAllowed] {exc}"
    if not target.exists():
        return "[NotFound] 目录不存在"
    if not target.is_dir():
        return "[NotADirectory] 目标不是目录"
    try:
        entries = sorted(p.name for p in target.iterdir())
    except OSError as exc:
        return f"[ListError] {type(exc).__name__}"
    if not entries:
        return "（空目录）"
    lines = [f"{name}{'/' if (target / name).is_dir() else ''}" for name in entries]
    shaped = shape_result("list_directory", ok=True, content="\n".join(lines))
    return shaped.content
