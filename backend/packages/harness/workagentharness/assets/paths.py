"""资产目录与实体路径（第 17 章）。

对齐 EvoFlow ``assets/paths.py``（快照 8e462a37）：
    EntityRef                        ← :74（本项目在 memory/entities.py，两类实体）
    sanitize_user_asset_id           ← :51
    assets_root                      ← :101
    workspace_asset_root             ← :105
    entity_root                      ← :174
    entity_relative_dir              ← :146
    resolve_workspace_path_for_entity_id ← :119

偏差：原版有四类实体，本项目只有 ``user`` / ``workspace``；资产根固定
``<cwd>/.wah/assets/``，不跟随原版的全局数据目录。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from workagentharness.memory.entities import EntityRef

ASSETS_DIRNAME = Path(".wah") / "assets"
_ID_MAX = 32
_ILLEGAL = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_asset_id(raw: str) -> str:
    """把任意 id 变成安全目录名：替换非法字符、截断、必要时追加 8 位哈希。

    哈希后缀解决"替换后撞名"：``../../etc`` 与 ``.._.._etc`` 都会变成 ``.._.._etc``，
    加哈希后互不覆盖，同时保留肉眼可读前缀。
    """
    original = str(raw or "").strip()
    cleaned = _ILLEGAL.sub("_", original)
    # 全是点的路径片段（"." / ".."）不能当目录名
    if cleaned.strip(".") == "":
        cleaned = "anon"
    changed = cleaned != original or len(cleaned) > _ID_MAX
    cleaned = cleaned[:_ID_MAX].strip("._-") or "anon"
    if changed:
        suffix = hashlib.sha256(original.encode("utf-8")).hexdigest()[:8]
        cleaned = f"{cleaned}-{suffix}"
    return cleaned


def assets_root(base_dir: str | Path) -> Path:
    return Path(base_dir) / ASSETS_DIRNAME


def entity_root(base_dir: str | Path, entity: EntityRef) -> Path:
    """实体自己的目录：``<cwd>/.wah/assets/<type>/<id>/``。"""
    return assets_root(base_dir) / entity.entity_type / sanitize_asset_id(entity.entity_id)


def entity_relative_dir(entity: EntityRef) -> str:
    """实体在资产根下的相对目录（写进产物记录用）。"""
    return f"{entity.entity_type}/{sanitize_asset_id(entity.entity_id)}"


def resolve_entity_path(base_dir: str | Path, entity: EntityRef, rel_path: str) -> Path:
    """把相对路径解析到实体目录内；越界（绝对路径 / ``..``）直接抛 ValueError。"""
    rel = str(rel_path or "").strip().replace("\\", "/")
    if not rel:
        raise ValueError("资产路径不能为空")
    if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
        raise ValueError(f"资产路径必须是相对路径: {rel_path!r}")
    if any(part == ".." for part in rel.split("/")):
        raise ValueError(f"资产路径不能包含 ..: {rel_path!r}")

    root = entity_root(base_dir, entity).resolve()
    target = (root / rel).resolve()
    # resolve() 之后再比较：符号链接也会被展开，防"软链越界"
    if target != root and root not in target.parents:
        raise ValueError(f"资产路径越出实体目录: {rel_path!r}")
    return target


__all__ = [
    "ASSETS_DIRNAME",
    "assets_root",
    "entity_relative_dir",
    "entity_root",
    "resolve_entity_path",
    "sanitize_asset_id",
]
