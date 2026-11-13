"""第 18 章：第四篇综合测试（折叠 → 记忆 → 注入 → 资产 → 反思）。

串的是真实链路：真 SQLite、真 checkpointer、真 RunService、真中间件，
不 mock 被测对象；每一段都用第 14–17 章的公开接口断言。
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from langchain_core.messages import HumanMessage

from workagentharness.assets.store import AssetStore
from workagentharness.assets.wrapup import list_wrapups, record_wrapup
from workagentharness.context.compaction_state import split_pinned
from workagentharness.memory.entities import EntityRef
from workagentharness.memory.middleware import MEMORY_MESSAGE_NAME, MemoryRuntimeMiddleware
from workagentharness.memory.store import MemoryStore
from workagentharness.persistence.db import open_database
from tests.chapters.helpers import ServiceBundle


class Part4IntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wah-ch18-")
        self.db = open_database(str(Path(self._tmp.name) / "part4.db"))
        self.store = MemoryStore(self.db)
        self.user = EntityRef("user", "local-user")
        self.memory = MemoryRuntimeMiddleware(self.store, thread_id="s1", entity=self.user)
        self.bundle = ServiceBundle(with_tools=False, middleware=[self.memory])

    def tearDown(self) -> None:
        self.bundle.close()
        self.db.close()
        self._tmp.cleanup()

    def test_turn_writes_memory_and_short_term(self) -> None:
        """真实跑一轮：偏好进长期，当前指令进短期。"""
        result = self.bundle.run_once("以后都必须用 4 空格缩进", session_id="s1")
        self.assertEqual(result.status, "completed")
        facts = self.store.facts(entity=self.user)
        self.assertEqual([f["content"] for f in facts], ["以后都必须用 4 空格缩进"])
        self.assertTrue(self.store.task_notes("s1"))

    def test_one_off_instruction_stays_short_term(self) -> None:
        """一次性指令不进长期，只留在当前 thread。"""
        self.bundle.run_once("这次先别看 tests 目录", session_id="s1")
        self.assertEqual(self.store.facts(entity=self.user), [])
        self.assertEqual(len(self.store.task_notes("s1")), 1)
        self.assertEqual(self.store.task_notes("s2"), [])

    def test_new_thread_recalls_long_term(self) -> None:
        """换会话后仍能召回长期记忆，并作为 pinned 消息注入。"""
        self.store.add_fact("项目统一 4 空格缩进", entity=self.user)
        other = MemoryRuntimeMiddleware(self.store, thread_id="s2", entity=self.user)
        update = other.before_model({"messages": []}, None)
        self.assertEqual(update["messages"][0].name, MEMORY_MESSAGE_NAME)
        self.assertIn("项目统一 4 空格缩进", update["messages"][0].content)

    def test_injected_memory_survives_fold(self) -> None:
        """注入的记忆是 pinned 消息，折叠时被保留（第 14 章语义在本篇生效）。"""
        self.store.add_fact("不要用 tab", entity=self.user)
        update = self.memory.before_model({"messages": []}, None)
        messages = [HumanMessage(content=f"旧消息 {i}") for i in range(10)] + update["messages"]
        kept, folded = split_pinned(messages)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].name, MEMORY_MESSAGE_NAME)
        self.assertEqual(len(folded), 10)

    def test_asset_and_wrapup_after_run(self) -> None:
        """产物落盘可读回；收尾交班记录可查。"""
        assets = AssetStore(self.db, Path(self._tmp.name))
        artifact = assets.write(self.user, "reports/part4.md", "# 第四篇验收\n")
        self.assertEqual(artifact["type"], "markdown")
        self.assertEqual(assets.read(self.user, "reports/part4.md"), "# 第四篇验收\n")

        run_id = self.bundle.run_once("以后都必须写验收记录", session_id="s1").run_id
        record_wrapup(
            self.db,
            run_id=run_id,
            thread_id="s1",
            outcome="完成第四篇集成",
            reflection="记忆注入改为 pinned 消息",
        )
        rows = list_wrapups(self.db, thread_id="s1")
        self.assertEqual(rows[0]["outcome"], "完成第四篇集成")

    def test_full_chain_shape(self) -> None:
        """一段落式断言：记忆、产物、交班、短期清理四件事都成立。"""
        self.bundle.run_once("以后都必须用 4 空格缩进", session_id="s1")
        self.assertTrue(self.store.facts(entity=self.user))
        assets = AssetStore(self.db, Path(self._tmp.name))
        assets.write(self.user, "a.md", "x")
        self.assertEqual(self.memory.clear_thread(), 1)
        self.assertEqual(self.store.task_notes("s1"), [])
        self.assertTrue(self.store.facts(entity=self.user))


if __name__ == "__main__":
    unittest.main()
