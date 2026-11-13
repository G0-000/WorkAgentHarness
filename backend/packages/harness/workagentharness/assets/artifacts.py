"""产物归一化（第 17 章）。

对齐 EvoFlow ``artifacts/chat_artifact.py``（快照 8e462a37）：
    normalize_artifact_type   ← :27
    make_artifact_id          ← :68
    normalize_chat_artifact   ← :86
    normalize_chat_artifacts  ← :197（limit=40）
    artifact_state_key        ← :221

偏差：原版 id 用五因子（type/path/url/content/name），本项目文件类产物只有
path + size + type，三因子足够判"是不是同一个文件"。
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

ARTIFACT_LIMIT = 40

_EXT_TO_TYPE = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".json": "json",
    ".log": "log",
    ".txt": "text",
    ".csv": "csv",
    ".html": "html",
    ".py": "code",
}


def normalize_artifact_type(raw: str | None, *, path: str = "") -> str:
    """显式类型优先；否则按扩展名推断；都没有则 ``file``。"""
    if raw:
        value = str(raw).strip().lower()
        if value:
            return value
    suffix = ("." + str(path).rsplit(".", 1)[-1].lower()) if "." in str(path) else ""
    return _EXT_TO_TYPE.get(suffix, "file")


def make_artifact_id(*, type_: str, path: str, size: int, name: str = "") -> str:
    raw = f"{type_}:{path}:{int(size)}:{name}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def artifact_state_key(*, type_: str, path: str, size: int) -> str:
    """去重键：类型 + 路径 + 大小。同键视为同一产物，不比较内容哈希。"""
    return f"{type_}|{path}|{int(size)}"


def normalize_chat_artifact(item: dict[str, Any]) -> dict[str, Any]:
    """补全 ``{id, type, name, path, size}`` 五字段，缺一不可。"""
    path = str(item.get("path") or "")
    size = int(item.get("size") or 0)
    type_ = normalize_artifact_type(item.get("type"), path=path)
    name = str(item.get("name") or (path.rsplit("/", 1)[-1] if path else ""))
    return {
        "id": item.get("id") or make_artifact_id(type_=type_, path=path, size=size, name=name),
        "type": type_,
        "name": name,
        "path": path,
        "size": size,
        "state_key": artifact_state_key(type_=type_, path=path, size=size),
    }


def normalize_chat_artifacts(items: Iterable[dict[str, Any]], *, limit: int = ARTIFACT_LIMIT) -> list[dict[str, Any]]:
    """去重 + 截断：同键覆盖旧记录，条数超限丢最早。"""
    kept: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for raw in items:
        artifact = normalize_chat_artifact(dict(raw))
        key = artifact["state_key"]
        if key not in kept:
            order.append(key)
        kept[key] = artifact
    artifacts = [kept[key] for key in order]
    if len(artifacts) > limit:
        artifacts = artifacts[-limit:]
    return artifacts


__all__ = [
    "ARTIFACT_LIMIT",
    "artifact_state_key",
    "make_artifact_id",
    "normalize_artifact_type",
    "normalize_chat_artifact",
    "normalize_chat_artifacts",
]
