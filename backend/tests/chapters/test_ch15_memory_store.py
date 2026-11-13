"""第 15 章：会话短期记忆与长期记忆（WAH-MEM-002–003）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from workagentharness.memory.entities import EntityRef
from workagentharness.memory.store import MemoryStore
from workagentharness.persistence.db import open_database


class MemoryStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wah-ch15-")
        self.db = open_database(str(Path(self._tmp.name) / "m.db"))
        self.store = MemoryStore(self.db, agent_name="default")
        self.user_a = EntityRef("user", "user-a")
        self.user_b = EntityRef("user", "user-b")

    def tearDown(self) -> None:
        self.db.close()
        self._tmp.cleanup()

    def test_add_fact_and_read_back(self) -> None:
        """长期事实写入后可读回，字段完整。"""
        fact_id = self.store.add_fact("项目统一用 4 空格缩进", entity=self.user_a)
        facts = self.store.facts(entity=self.user_a)
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["id"], fact_id)
        self.assertEqual(facts[0]["category"], "preference")
        self.assertEqual(facts[0]["confidence"], 1.0)

    def test_same_fact_is_idempotent(self) -> None:
        """同一实体同一内容重复写入只留一条（幂等，不越积越脏）。"""
        self.store.add_fact("不要用 tab", entity=self.user_a)
        self.store.add_fact("不要用 tab", entity=self.user_a)
        self.assertEqual(len(self.store.facts(entity=self.user_a)), 1)

    def test_entities_are_isolated(self) -> None:
        """不同实体的长期记忆互不可见（原版按 agent/user 隔离）。"""
        self.store.add_fact("偏好 A", entity=self.user_a)
        self.store.add_fact("偏好 B", entity=self.user_b)
        self.assertEqual([f["content"] for f in self.store.facts(entity=self.user_a)], ["偏好 A"])
        self.assertEqual([f["content"] for f in self.store.facts(entity=self.user_b)], ["偏好 B"])

    def test_task_notes_are_thread_scoped(self) -> None:
        """短期记忆按 thread 隔离，换 thread 读不到。"""
        self.store.add_task_note("t1", "user", "这次先别看 tests")
        self.store.add_task_note("t2", "user", "另一件事")
        self.assertEqual(len(self.store.task_notes("t1")), 1)
        self.assertEqual(self.store.task_notes("t2")[0]["content"], "另一件事")

    def test_clear_task_memory_only_clears_one_thread(self) -> None:
        """清理返回删除条数，且不影响其他 thread。"""
        self.store.add_task_note("t1", "user", "x")
        self.store.add_task_note("t1", "assistant", "y")
        self.store.add_task_note("t2", "user", "z")
        self.assertEqual(self.store.clear_task_memory("t1"), 2)
        self.assertEqual(self.store.task_notes("t1"), [])
        self.assertEqual(len(self.store.task_notes("t2")), 1)

    def test_combined_memory_shape(self) -> None:
        """合并视图返回 long_term / short_term / merged 三字段。"""
        self.store.add_fact("必须写测试", entity=self.user_a)
        self.store.add_task_note("t1", "user", "本轮任务：改文档")
        combined = self.store.get_combined_memory("t1", entity=self.user_a)
        self.assertEqual(set(combined.keys()), {"long_term", "short_term", "merged"})
        self.assertIn("[long] 必须写测试", combined["merged"])
        self.assertIn("[user] 本轮任务：改文档", combined["merged"])

    def test_combined_memory_without_thread(self) -> None:
        """不传 thread 时只有长期记忆。"""
        self.store.add_fact("偏好", entity=self.user_a)
        combined = self.store.get_combined_memory()
        self.assertEqual(combined["short_term"], [])

    def test_delete_fact(self) -> None:
        """删除事实；再删同一条返回 False。"""
        fact_id = self.store.add_fact("临时偏好", entity=self.user_a)
        self.assertTrue(self.store.delete_fact(fact_id))
        self.assertFalse(self.store.delete_fact(fact_id))

    def test_invalid_inputs_raise(self) -> None:
        """非法分类 / 置信度 / 空内容必须报错，不能静默写脏数据。"""
        with self.assertRaises(ValueError):
            self.store.add_fact("x", category="unknown", entity=self.user_a)
        with self.assertRaises(ValueError):
            self.store.add_fact("x", confidence=1.5, entity=self.user_a)
        with self.assertRaises(ValueError):
            self.store.add_fact("   ", entity=self.user_a)

    def test_invalid_entity_rejected(self) -> None:
        """实体类型或 id 非法时构造即失败（路径安全的第一道）。"""
        with self.assertRaises(ValueError):
            EntityRef("employee", "e1")
        with self.assertRaises(ValueError):
            EntityRef("user", "../etc")


if __name__ == "__main__":
    unittest.main()
