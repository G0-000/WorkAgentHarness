"""第 14 章验收：上下文来源、预算与压缩恢复（WAH-MEM-001/008、WAH-TOOL-007）。

对应教程：四-上下文记忆和长期资产/14. 上下文来源预算与压缩恢复.md
被测对象全部是本项目真实模块，不 mock：
    context/token_budget.py
    context/tool_history_merge.py
    context/compaction_state.py
    middleware/context_compaction.py（折叠集成点）
"""

from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from workagentharness.context.compaction_state import (
    is_pinned, last_fold_record, pin_message, reset_fold_records, split_pinned,
)
from workagentharness.context.token_budget import (
    DEFAULT_CHARS_PER_TOKEN, TokenEstimate, current_estimator_name,
    default_estimator, estimate_request_tokens, estimate_tokens,
    reset_token_estimator, set_token_estimator,
)
from workagentharness.context.tool_history_merge import build_tool_round_entries, plan_tool_history_merge
from workagentharness.middleware.context_compaction import (
    KEEP_RECENT_MESSAGES, MAX_CONTEXT_CHARS, ContextCompactionMiddleware,
    _fold_counts, _skip_once,
    compaction_fold_detail, compaction_fold_msg_counts, compaction_last_bound_estimate,
    mark_skip_compaction_once,
)


def _messages(count: int, size: int, prefix: str = "m") -> list[HumanMessage]:
    return [HumanMessage(content="x" * size, id=f"{prefix}{i}") for i in range(count)]


def _read_file_round(round_no: int, path: str, body: str = "file body") -> list:
    """一次"读文件"产生的两条消息：AI tool_call + ToolMessage。"""
    call_id = f"c{round_no}"
    return [
        AIMessage(
            content="",
            id=f"ai{round_no}",
            tool_calls=[
                {"id": call_id, "name": "read_file", "args": {"path": path}, "type": "tool_call"}
            ],
        ),
        ToolMessage(content=body, tool_call_id=call_id, name="read_file", id=f"t{round_no}"),
    ]


class TokenBudgetTest(unittest.TestCase):
    def tearDown(self):
        # 估算器是 ContextVar，跨用例会残留，必须复位
        self.assertEqual(DEFAULT_CHARS_PER_TOKEN, 3)

    def test_default_estimator_is_chars_over_three(self):
        self.assertEqual(estimate_tokens("a" * 300), 100)
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("ab"), 1)  # 非空至少算 1
        self.assertEqual(default_estimator("x" * 3000), 1000)

    def test_pluggable_estimator(self):
        token = set_token_estimator(lambda text: 1)
        try:
            self.assertEqual(estimate_tokens("whatever"), 1)
            self.assertEqual(current_estimator_name(), "custom")
        finally:
            reset_token_estimator(token)
        self.assertEqual(estimate_tokens("a" * 300), 100)
        self.assertEqual(current_estimator_name(), "chars//3")

    def test_request_estimate_splits_system_and_messages(self):
        estimate = estimate_request_tokens(_messages(2, 300), system_prompt="s" * 300)
        self.assertIsInstance(estimate, TokenEstimate)
        self.assertEqual(estimate.system_tokens, 100)
        self.assertEqual(estimate.message_tokens, 200)
        self.assertEqual(estimate.total_tokens, 300)
        self.assertEqual(estimate.to_meta(), {"system_tokens": 100, "message_tokens": 200, "total_tokens": 300})

    def test_explicit_estimator_wins_over_context_one(self):
        token = set_token_estimator(lambda text: 999)
        try:
            self.assertEqual(estimate_tokens("abc", estimator=lambda text: 2), 2)
        finally:
            reset_token_estimator(token)


class ToolHistoryMergeTest(unittest.TestCase):
    def test_same_file_read_three_times_keeps_last(self):
        messages = [*_read_file_round(1, "/a.py"), *_read_file_round(2, "/a.py"), *_read_file_round(3, "/a.py")]
        entries = build_tool_round_entries(messages)
        self.assertEqual([e.merge_key for e in entries], ["file:/a.py"] * 3)
        drop, merged = plan_tool_history_merge(messages)
        self.assertEqual(drop, ["t1", "t2"])
        self.assertEqual(merged, 2)

    def test_different_files_not_merged(self):
        messages = [*_read_file_round(1, "/a.py"), *_read_file_round(2, "/b.py")]
        drop, merged = plan_tool_history_merge(messages)
        self.assertEqual((drop, merged), ([], 0))

    def test_preserve_ids_excluded(self):
        messages = [*_read_file_round(1, "/a.py"), *_read_file_round(2, "/a.py")]
        drop, merged = plan_tool_history_merge(messages, preserve_ids=frozenset({"t1"}))
        self.assertEqual((drop, merged), ([], 0))

    def test_tool_without_path_not_merged(self):
        messages = [
            ToolMessage(content="a", tool_call_id="c1", name="calculator", id="t1"),
            ToolMessage(content="b", tool_call_id="c2", name="calculator", id="t2"),
        ]
        self.assertEqual(plan_tool_history_merge(messages), ([], 0))


class PinnedTest(unittest.TestCase):
    def test_pin_and_split(self):
        pinned = HumanMessage(content="命名规范：4 空格缩进", id="p")
        pin_message(pinned, reason="用户显式规范")
        self.assertTrue(is_pinned(pinned))
        kept, rest = split_pinned([pinned, HumanMessage(content="x", id="n")])
        self.assertEqual([m.id for m in kept], ["p"])
        self.assertEqual([m.id for m in rest], ["n"])


class CompactionIntegrationTest(unittest.TestCase):
    def setUp(self):
        _fold_counts.set(None)
        _skip_once.set(False)
        reset_fold_records()
        self.middleware = ContextCompactionMiddleware()

    def test_constants_unchanged(self):
        self.assertEqual(MAX_CONTEXT_CHARS, 12000)
        self.assertEqual(KEEP_RECENT_MESSAGES, 6)

    def test_short_context_writes_no_record(self):
        self.assertIsNone(self.middleware.before_model({"messages": _messages(5, 100)}, None))
        self.assertIsNone(last_fold_record())

    def test_fold_records_counts_tokens_and_estimator(self):
        result = self.middleware.before_model({"messages": _messages(8, 2000)}, None)
        self.assertIsNotNone(result)
        self.assertEqual(compaction_fold_msg_counts(), (8, 7))
        detail = compaction_fold_detail()
        self.assertEqual((detail.before, detail.after, detail.folded), (8, 7, 1))
        self.assertEqual(detail.merged_tool_messages, 0)
        self.assertGreater(detail.total_tokens, 0)
        self.assertEqual(detail.estimator, "chars//3")
        self.assertEqual(compaction_last_bound_estimate().total_tokens, detail.total_tokens)

    def test_pinned_head_message_survives_fold(self):
        messages = _messages(8, 2000)
        pin_message(messages[0])  # 第 0 条是用户定的规范，不许折
        result = self.middleware.before_model({"messages": messages}, None)
        removed_ids = [getattr(m, "id", "") for m in result["messages"] if type(m).__name__ == "RemoveMessage"]
        self.assertNotIn("m0", removed_ids)
        detail = compaction_fold_detail()
        self.assertEqual(detail.pinned_kept, 1)
        self.assertEqual(compaction_fold_msg_counts(), (8, 8))  # 1 钉住 + 1 摘要 + 6 最近

    def test_duplicate_tool_reads_merged_in_fold(self):
        messages = [*_read_file_round(1, "/a.py"), *_read_file_round(2, "/a.py")]
        messages += _messages(6, 2000, prefix="pad")  # 撑到阈值以上，且构成"最近 6 条"
        result = self.middleware.before_model({"messages": messages}, None)
        self.assertIsNotNone(result)
        self.assertEqual(compaction_fold_detail().merged_tool_messages, 1)
        self.assertTrue(any(type(m).__name__ == "RemoveMessage" for m in result["messages"]))

    def test_skip_once_still_consumed(self):
        from workagentharness.middleware.context_compaction import mark_skip_compaction_once
        mark_skip_compaction_once()
        self.assertIsNone(self.middleware.before_model({"messages": _messages(8, 2000)}, None))
        self.assertIsNone(last_fold_record())


if __name__ == "__main__":
    unittest.main()
