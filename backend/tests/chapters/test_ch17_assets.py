"""第 17 章：资产、产物、事项与反思（WAH-MEM-006–007）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from workagentharness.assets.artifacts import (
    ARTIFACT_LIMIT,
    artifact_state_key,
    normalize_artifact_type,
    normalize_chat_artifacts,
)
from workagentharness.assets.paths import entity_root, resolve_entity_path, sanitize_asset_id
from workagentharness.assets.store import AssetStore
from workagentharness.assets.wrapup import list_wrapups, record_wrapup
from workagentharness.memory.entities import EntityRef
from workagentharness.persistence.db import open_database


class AssetPathTest(unittest.TestCase):
    def test_sanitize_replaces_illegal_chars(self) -> None:
        """非法字符被替换，路径片段不再可执行。"""
        cleaned = sanitize_asset_id("../../etc/passwd")
        self.assertNotIn("..", cleaned)
        self.assertNotIn("/", cleaned)

    def test_sanitize_collision_gets_hash_suffix(self) -> None:
        """替换后会撞名的两个 id，加上哈希后缀后互不覆盖。"""
        self.assertNotEqual(sanitize_asset_id("a b"), sanitize_asset_id("a/b"))

    def test_resolve_rejects_absolute_and_traversal(self) -> None:
        """绝对路径和 .. 都必须在解析阶段被拒绝。"""
        entity = EntityRef("user", "local-user")
        with self.assertRaises(ValueError):
            resolve_entity_path("/tmp", entity, "/etc/passwd")
        with self.assertRaises(ValueError):
            resolve_entity_path("/tmp", entity, "../../etc/passwd")
        with self.assertRaises(ValueError):
            resolve_entity_path("/tmp", entity, "")

    def test_resolve_stays_inside_entity_root(self) -> None:
        """正常相对路径解析到实体目录之内。"""
        entity = EntityRef("user", "local-user")
        target = resolve_entity_path("/tmp", entity, "reports/a.md")
        self.assertIn(entity_root("/tmp", entity).resolve(), target.parents)


class ArtifactTest(unittest.TestCase):
    def test_type_inference(self) -> None:
        """扩展名推断：md→markdown、png→image，未知→file。"""
        self.assertEqual(normalize_artifact_type(None, path="a.md"), "markdown")
        self.assertEqual(normalize_artifact_type(None, path="a.png"), "image")
        self.assertEqual(normalize_artifact_type(None, path="a.bin"), "file")
        self.assertEqual(normalize_artifact_type("custom", path="a.md"), "custom")

    def test_state_key_dedupes_same_file(self) -> None:
        """同 type+path+size 视为同一产物；size 变了才是新产物。"""
        key = artifact_state_key(type_="markdown", path="u/a.md", size=10)
        same = normalize_chat_artifacts(
            [
                {"path": "u/a.md", "size": 10, "name": "a.md"},
                {"path": "u/a.md", "size": 10, "name": "a.md"},
                {"path": "u/a.md", "size": 11, "name": "a.md"},
            ]
        )
        self.assertEqual(len(same), 2)
        self.assertEqual(same[0]["state_key"], key)

    def test_limit_40_keeps_latest(self) -> None:
        """超过 40 条丢最早，保留最新。"""
        items = [{"path": f"a/{i}.md", "size": 1} for i in range(45)]
        kept = normalize_chat_artifacts(items)
        self.assertEqual(len(kept), ARTIFACT_LIMIT)
        self.assertIn("44.md", kept[-1]["name"])


class AssetStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wah-ch17-")
        self.db = open_database(str(Path(self._tmp.name) / "a.db"))
        self.base = Path(self._tmp.name)
        self.store = AssetStore(self.db, self.base)
        self.user = EntityRef("user", "local-user")

    def tearDown(self) -> None:
        self.db.close()
        self._tmp.cleanup()

    def test_write_read_roundtrip(self) -> None:
        """写文件真实落盘，且能按同一路径读回。"""
        artifact = self.store.write(self.user, "reports/summary.md", "# 总结\n内容")
        self.assertEqual(artifact["type"], "markdown")
        self.assertEqual(artifact["name"], "summary.md")
        self.assertEqual(self.store.read(self.user, "reports/summary.md"), "# 总结\n内容")
        self.assertIn("reports/summary.md", self.store.list_assets(self.user))

    def test_entities_do_not_overwrite(self) -> None:
        """两个实体写同名文件互不影响。"""
        other = EntityRef("workspace", "proj-x")
        self.store.write(self.user, "a.md", "user")
        self.store.write(other, "a.md", "workspace")
        self.assertEqual(self.store.read(self.user, "a.md"), "user")
        self.assertEqual(self.store.read(other, "a.md"), "workspace")

    def test_artifacts_table_dedupes(self) -> None:
        """同 size 重复写同一路径只登记一条；size 变化才新增。"""
        self.store.write(self.user, "a.md", "123")
        self.store.write(self.user, "a.md", "123")
        self.assertEqual(len(self.store.artifacts()), 1)
        self.store.write(self.user, "a.md", "123456")
        self.assertEqual(len(self.store.artifacts()), 2)

    def test_read_missing_raises(self) -> None:
        """读不存在的资产报 FileNotFoundError。"""
        with self.assertRaises(FileNotFoundError):
            self.store.read(self.user, "none.md")

    def test_escape_write_rejected(self) -> None:
        """写入时越界路径被拒（与 7.2 只读边界一起构成路径守卫）。"""
        with self.assertRaises(ValueError):
            self.store.write(self.user, "../evil.md", "x")


class WrapupTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wah-ch17w-")
        self.db = open_database(str(Path(self._tmp.name) / "w.db"))

    def tearDown(self) -> None:
        self.db.close()
        self._tmp.cleanup()

    def test_record_and_list(self) -> None:
        """交班三件套落库，可按 thread 查回。"""
        record_wrapup(
            self.db,
            run_id="r1",
            thread_id="t1",
            outcome="完成第 17 章代码",
            reflection="文档里的偏差需要同步",
            initiatives="补资产工具",
        )
        rows = list_wrapups(self.db, thread_id="t1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reflection"], "文档里的偏差需要同步")
        self.assertEqual(list_wrapups(self.db, thread_id="t2"), [])

    def test_empty_outcome_rejected(self) -> None:
        """没写 outcome 的交班记录不允许落库。"""
        with self.assertRaises(ValueError):
            record_wrapup(self.db, run_id="r1", thread_id="t1", outcome="  ")


if __name__ == "__main__":
    unittest.main()
