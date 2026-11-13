"""记忆与资产的实体坐标（第 15–17 章共用）。

对齐 EvoFlow ``assets/paths.py:74 EntityRef``：实体类型只有四类，本项目只用两类
（``user`` / ``workspace``），``normalized()`` 对非法 id 直接抛 ``ValueError``。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ALLOWED_ENTITY_TYPES = ("user", "workspace")
_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@dataclass(frozen=True)
class EntityRef:
    """一个"记忆/资产归属于谁"的坐标。"""

    entity_type: str
    entity_id: str

    def __post_init__(self) -> None:
        if self.entity_type not in ALLOWED_ENTITY_TYPES:
            raise ValueError(f"不支持的实体类型: {self.entity_type}")
        if not _ID_PATTERN.match(self.entity_id or ""):
            raise ValueError(f"非法的实体 id: {self.entity_id!r}")

    def normalized(self) -> tuple[str, str]:
        """返回 (类型, id)，供存储层当键用。"""
        return (self.entity_type, self.entity_id)

    def as_dict(self) -> dict[str, str]:
        return {"entity_type": self.entity_type, "entity_id": self.entity_id}


__all__ = ["ALLOWED_ENTITY_TYPES", "EntityRef"]
