"""第 16 章：记忆巩固、抽取与提示注入（WAH-MEM-004–005）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from langchain_core.messages import HumanMessage

from workagentharness.memory.entities import EntityRef
from workagentharness.memory.extract import extract_facts, should_persist_long_term
from workagentharness.memory.injection import (
    CONTEXT_MAX_CHARS,
    format_memory_for_injection,
    standing_fact_allowed,
)
from workagentharness.memory.middleware import MEMORY_MESSAGE_NAME, MemoryRuntimeMiddleware
from workagentharness.memory.store import MemoryStore
from workagentharness.persistence.db import open_database


class ExtractFactsTest(unittest.TestCase):
    def test_strong_preference_is_1_0(self) -> None:
        """显式偏好句式 → preference / 1.0。"""
        facts = extract_facts("以后都必须用 4 空格缩进，不要用 tab")
        self.assertEqual(len(facts), 1)
        self.assertEqual((facts[0].category, facts[0].confidence), ("preference", 1.0))

    def test_hedged_preference_is_0_6(self) -> None:
        """含"可能/大概" → 置信度降到 0.6，不进长期。"""
        facts = extract_facts("以后可能用 tab 吧")
        self.assertEqual(facts[0].confidence, 0.6)
        self.assertFalse(should_persist_long_term(facts[0]))

    def test_one_off_instruction_is_context(self) -> None:
        """"这次先别看 tests" → context / 0.8，且不进长期。"""
        facts = extract_facts("这次先别看 tests 目录")
        self.assertEqual(facts[0].category, "context")
        self.assertFalse(should_persist_long_term(facts[0]))

    def test_knowledge_question_is_not_memory(self) -> None:
        """问原理/要介绍 = 知识请求，不进记忆（交第五篇知识库）。"""
        self.assertEqual(extract_facts("介绍下这个模块的实现原理"), [])

    def test_repeated_action_is_behavior(self) -> None:
        """"每次…" → behavior。"""
        facts = extract_facts("每次提交前都先跑单元测试")
        self.assertEqual(facts[0].category, "behavior")

    def test_plain_chat_extracts_nothing(self) -> None:
        """普通闲聊不硬造事实。"""
        self.assertEqual(extract_facts("今天天气不错"), [])


class InjectionFilterTest(unittest.TestCase):
    def test_rules(self) -> None:
        """5 条过滤规则：空、类别、超长、context 长度/置信、compact。"""
        self.assertFalse(standing_fact_allowed({"content": "", "category": "preference"}))
        self.assertFalse(standing_fact_allowed({"content": "x", "category": "knowledge"}))
        self.assertFalse(standing_fact_allowed({"content": "x" * 401, "category": "preference"}))
        self.assertFalse(
            standing_fact_allowed({"content": "这次先别看 tests", "category": "context", "confidence": 0.7})
        )
        self.assertFalse(
            standing_fact_allowed({"content": "长" * (CONTEXT_MAX_CHARS + 1), "category": "context", "confidence": 0.9})
        )
        self.assertTrue(standing_fact_allowed({"content": "x", "category": "preference", "confidence": 1.0}))
        self.assertTrue(
            standing_fact_allowed({"content": "短", "category": "context", "confidence": 0.8})
        )
        self.assertFalse(
            standing_fact_allowed({"content": "x", "category": "behavior", "confidence": 1.0}, chat_compact=True)
        )

    def test_format_skips_filtered(self) -> None:
        """格式化只输出通过过滤的条目；全部被筛掉返回空串。"""
        block = format_memory_for_injection(
            [
                {"content": "必须 4 空格", "category": "preference", "confidence": 1.0},
                {"content": "db 表结构", "category": "knowledge", "confidence": 1.0},
            ]
        )
        self.assertIn("必须 4 空格", block)
        self.assertNotIn("db 表结构", block)
        self.assertEqual(format_memory_for_injection([{"content": "", "category": "preference"}]), "")


class MemoryMiddlewareTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wah-ch16-")
        self.db = open_database(str(Path(self._tmp.name) / "m.db"))
        self.store = MemoryStore(self.db)
        self.entity = EntityRef("user", "local-user")
        self.middleware = MemoryRuntimeMiddleware(self.store, thread_id="t1", entity=self.entity)

    def tearDown(self) -> None:
        self.db.close()
        self._tmp.cleanup()

    def test_inject_once_and_pinned(self) -> None:
        """有记忆时注入一条 pinned 消息；同一 thread 第二次不再注入。"""
        self.store.add_fact("必须 4 空格缩进", entity=self.entity)
        update = self.middleware.before_model({"messages": []}, None)
        self.assertEqual(len(update["messages"]), 1)
        message = update["messages"][0]
        self.assertEqual(message.name, MEMORY_MESSAGE_NAME)
        self.assertTrue(message.additional_kwargs.get("pinned"))
        self.assertIsNone(self.middleware.before_model({"messages": []}, None))

    def test_no_memory_no_injection(self) -> None:
        """库里没记忆时不插入空消息。"""
        self.assertIsNone(self.middleware.before_model({"messages": []}, None))

    def test_after_model_extracts_and_persists(self) -> None:
        """轮次结束抽取：偏好进长期，一次性指令只进短期。"""
        state = {"messages": [HumanMessage(content="以后都必须用 4 空格缩进")]}
        self.middleware.after_model(state, None)
        self.assertEqual(len(self.store.facts(entity=self.entity)), 1)

        state2 = {"messages": [HumanMessage(content="这次先别看 tests 目录")]}
        self.middleware.after_model(state2, None)
        self.assertEqual(len(self.store.facts(entity=self.entity)), 1)
        self.assertTrue(any(n["content"].startswith("这次") for n in self.store.task_notes("t1")))

    def test_clear_thread(self) -> None:
        """收尾清理短期记忆，并允许下个任务重新注入。"""
        self.store.add_task_note("t1", "user", "x")
        self.assertGreaterEqual(self.middleware.clear_thread(), 1)
        self.assertEqual(self.store.task_notes("t1"), [])


if __name__ == "__main__":
    unittest.main()
