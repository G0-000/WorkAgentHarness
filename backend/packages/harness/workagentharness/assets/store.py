"""资产存储：写文件 + 登记产物（第 17 章）。

对齐 EvoFlow ``tools/builtins/assets_tool.py`` 的读写语义：
    写：解析实体 → 规范化相对路径 → 计算绝对路径 → 越界拒绝 → 落盘 → 登记产物
    读：同一个路径解析规则，读到实体自己目录里的内容

与设计初稿的偏差（本轮按用户要求改为实现）：
    设计初稿写"本章只设计不实现"，理由是缺写文件能力与 HTTP 服务。本轮补了
    **受路径守卫约束的写能力**（只允许写 ``<cwd>/.wah/assets/<type>/<id>/`` 之内），
    但"在浏览器里点开产物"仍缺 HTTP 服务，属于第十篇，本章只做到"文件真实落盘 + 产物可查"。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workagentharness.assets.artifacts import normalize_chat_artifact, normalize_chat_artifacts
from workagentharness.assets.paths import entity_relative_dir, entity_root, resolve_entity_path
from workagentharness.memory.entities import EntityRef
from workagentharness.memory.schema import ensure_memory_tables


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AssetStore:
    """按实体分开的资产目录 + ``artifacts`` 表。"""

    def __init__(self, connection: sqlite3.Connection, base_dir: str | Path) -> None:
        self.connection = connection
        self.base_dir = Path(base_dir)
        ensure_memory_tables(connection)

    # ---------- 写 ----------
    def write(self, entity: EntityRef, rel_path: str, content: str) -> dict[str, Any]:
        """写一个文件并登记产物；返回归一化后的产物记录。"""
        target = resolve_entity_path(self.base_dir, entity, rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        rel_in_entity = target.relative_to(entity_root(self.base_dir, entity).resolve()).as_posix()
        artifact = normalize_chat_artifact(
            {
                "path": f"{entity_relative_dir(entity)}/{rel_in_entity}",
                "size": target.stat().st_size,
                "name": target.name,
            }
        )
        self._upsert_artifact(artifact)
        return artifact

    def _upsert_artifact(self, artifact: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO artifacts(id, state_key, type, name, path, size, created_at) VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(state_key) DO UPDATE SET id=excluded.id, created_at=excluded.created_at",
            (
                artifact["id"],
                artifact["state_key"],
                artifact["type"],
                artifact["name"],
                artifact["path"],
                artifact["size"],
                _now(),
            ),
        )
        self.connection.commit()

    # ---------- 读 ----------
    def read(self, entity: EntityRef, rel_path: str) -> str:
        target = resolve_entity_path(self.base_dir, entity, rel_path)
        if not target.is_file():
            raise FileNotFoundError(f"资产不存在: {rel_path}")
        return target.read_text(encoding="utf-8")

    def list_assets(self, entity: EntityRef) -> list[str]:
        root = entity_root(self.base_dir, entity)
        if not root.exists():
            return []
        return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())

    def artifacts(self, *, limit: int = 40) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT id, type, name, path, size FROM artifacts ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return normalize_chat_artifacts([dict(row) for row in rows], limit=limit)


__all__ = ["AssetStore"]
