"""资产与产物层（第四篇第 17 章）。

对应 EvoFlow：
    assets/paths.py            ← paths.py
    artifacts/chat_artifact.py ← artifacts.py
    tools/builtins/assets_tool.py ← store.py（读写语义，不含 LangChain 工具封装）
    proactive_submit_work      ← wrapup.py（只存 outcome/reflection/initiatives）
"""

from __future__ import annotations

from workagentharness.assets.artifacts import (
    ARTIFACT_LIMIT,
    artifact_state_key,
    make_artifact_id,
    normalize_artifact_type,
    normalize_chat_artifact,
    normalize_chat_artifacts,
)
from workagentharness.assets.paths import (
    assets_root,
    entity_relative_dir,
    entity_root,
    resolve_entity_path,
    sanitize_asset_id,
)
from workagentharness.assets.store import AssetStore
from workagentharness.assets.wrapup import list_wrapups, record_wrapup

__all__ = [
    "ARTIFACT_LIMIT",
    "AssetStore",
    "artifact_state_key",
    "assets_root",
    "entity_relative_dir",
    "entity_root",
    "list_wrapups",
    "make_artifact_id",
    "normalize_artifact_type",
    "normalize_chat_artifact",
    "normalize_chat_artifacts",
    "record_wrapup",
    "resolve_entity_path",
    "sanitize_asset_id",
]
