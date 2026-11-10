"""第 11 章验收：中间件调用链、上下文折叠与自动续跑上限（WAH-TOOL-005/007/008、MEM-001/008）。

对应教程：11. Middleware上下文整理与本地调度。
"""

from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from workagentharness.middleware.context_compaction import (
    KEEP_RECENT_MESSAGES, MAX_CONTEXT_CHARS, ContextCompactionMiddleware,
    _fold_counts, _skip_once,
    compaction_fold_msg_counts, compaction_folded_this_call,
    consume_skip_compaction_once, mark_skip_compaction_once,
)
from workagentharness.middleware.goal_auto_continue import (
    MAX_STEPS, GoalAutoContinueMiddleware, current_step_count, reset_step_count,
)
from workagentharness.middleware.tool_audit import ToolAuditMiddleware


def _messages(count: int, size: int) -> list[HumanMessage]:
    return [HumanMessage(content="x" * size, id=f"m{i}") for i in range(count)]


class CompactionTest(unittest.TestCase):
    def setUp(self):
        # 折叠结果存在 ContextVar 里、跨用例会残留；每个用例先复位，避免顺序依赖
        _fold_counts.set(None)
        _skip_once.set(False)
        self.middleware = ContextCompactionMiddleware()

    def test_constants(self):
        self.assertEqual(MAX_CONTEXT_CHARS, 12000)
        self.assertEqual(KEEP_RECENT_MESSAGES, 6)

    def test_short_context_untouched(self):
        result = self.middleware.before_model({"messages": _messages(5, 100)}, None)
        self.assertIsNone(result)
        self.assertFalse(compaction_folded_this_call())

    def test_long_context_folds_head(self):
        messages = _messages(8, 2000)  # 16000 字符 > 12000
        result = self.middleware.before_model({"messages": messages}, None)
        self.assertIsNotNone(result)
        self.assertEqual(compaction_fold_msg_counts(), (8, 7))  # 折叠 2 条 + 1 条摘要
        self.assertTrue(any(type(m).__name__ == "RemoveMessage" for m in result["messages"]))
        summary = result["messages"][-1]
        self.assertEqual(summary.name, "context_summary")

    def test_skip_compaction_once(self):
        # 标记后第一次 before_model 应直接放过；标记随即被消耗掉
        mark_skip_compaction_once()
        self.assertIsNone(self.middleware.before_model({"messages": _messages(8, 2000)}, None))
        self.assertFalse(consume_skip_compaction_once())
        # 标记已消耗，再跑同规模上下文就会真的折叠
        self.assertIsNotNone(self.middleware.before_model({"messages": _messages(8, 2000)}, None))


class GoalMiddlewareTest(unittest.TestCase):
    def setUp(self):
        self.middleware = GoalAutoContinueMiddleware()
        reset_step_count()

    def _state(self, content: str, tool_calls=None):
        return {"messages": [HumanMessage(content="hi"), AIMessage(content=content, tool_calls=tool_calls or [])]}

    def test_limit_is_eight(self):
        self.assertEqual(MAX_STEPS, 8)

    def test_finished_round_ends(self):
        result = self.middleware.after_model(self._state("已完成"), None)
        self.assertEqual(result, {"jump_to": "end"})

    def test_unfinished_marker_continues(self):
        result = self.middleware.after_model(self._state("下一步继续做"), None)
        self.assertEqual(result["jump_to"], "model")
        self.assertEqual(current_step_count(), 1)

    def test_stops_at_limit(self):
        for _ in range(MAX_STEPS):
            self.middleware.after_model(self._state("下一步"), None)
        result = self.middleware.after_model(self._state("下一步"), None)
        self.assertEqual(result, {"jump_to": "end"})


class ToolAuditTest(unittest.TestCase):
    def test_logs_start_and_end(self):
        class Request:
            tool_call = {"name": "calculator", "args": {"expression": "1+1"}, "id": "c1"}

        middleware = ToolAuditMiddleware()
        with self.assertLogs("workagent.tools", level="INFO") as captured:
            result = middleware.wrap_tool_call(
                Request(), lambda _req: ToolMessage(content="2", tool_call_id="c1", name="calculator")
            )
        joined = "\n".join(captured.output)
        self.assertIn("tool.start name=calculator", joined)
        self.assertIn("tool.end name=calculator", joined)
        self.assertEqual(result.content, "2")

    def test_failure_logged_and_reraised(self):
        class Request:
            tool_call = {"name": "boom", "args": {}, "id": "c2"}

        def handler(_req):
            raise ValueError("x")

        middleware = ToolAuditMiddleware()
        with self.assertLogs("workagent.tools", level="WARNING") as captured:
            with self.assertRaises(ValueError):
                middleware.wrap_tool_call(Request(), handler)
        self.assertIn("tool.fail name=boom", "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()
