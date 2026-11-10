"""第 4 章验收：Agent 构建、单轮执行与同 thread 恢复（WAH-RUN-003/004）。

对应教程：4. Agent构建角色与单轮执行。
用内存 checkpointer，只验证"构建 + 两轮"；SQLite 持久化留给第 5 章。
"""

from __future__ import annotations

import unittest

from langgraph.checkpoint.memory import InMemorySaver

from workagentharness.agents.lead_agent.agent import DEFAULT_SYSTEM_PROMPT, make_lead_agent
from workagentharness.config.model_config import ChatModelConfig
from workagentharness.models.factory import create_chat_model


class AgentTest(unittest.TestCase):
    def setUp(self):
        config = ChatModelConfig(provider="fake", model="tutorial-fake", temperature=0)
        self.agent = make_lead_agent(create_chat_model(config), checkpointer=InMemorySaver())
        self.config = {"configurable": {"thread_id": "t1"}}

    def test_single_turn(self):
        result = self.agent.invoke({"messages": [("user", "你好")]}, self.config)
        self.assertEqual(str(result["messages"][-1].content), "已收到（第 1 轮）：你好")

    def test_same_thread_counts_second_round(self):
        self.agent.invoke({"messages": [("user", "第一句")]}, self.config)
        result = self.agent.invoke({"messages": [("user", "第二句")]}, self.config)
        # 能报“第 2 轮”说明 checkpoint 把上一轮历史带回来了
        self.assertEqual(str(result["messages"][-1].content), "已收到（第 2 轮）：第二句")

    def test_new_thread_starts_from_round_one(self):
        self.agent.invoke({"messages": [("user", "第一句")]}, self.config)
        fresh = self.agent.invoke(
            {"messages": [("user", "另一条 thread")]},
            {"configurable": {"thread_id": "t2"}},
        )
        self.assertIn("第 1 轮", str(fresh["messages"][-1].content))

    def test_system_prompt_forbids_fabrication(self):
        self.assertIn("不要编造事实", DEFAULT_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
