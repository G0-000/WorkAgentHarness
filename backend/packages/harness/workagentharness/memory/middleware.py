"""记忆中间件：轮次结束抽取事实，下一轮把记忆注入上下文（第 15–16 章）。

为什么用 middleware：
    记忆是横切关注点。写在 CLI 或 Agent 里会让"读记忆/写记忆"和业务逻辑耦合；
    挂 ``before_model`` / ``after_model`` 后，所有走 ``create_agent`` 的入口都自动生效。

注入形态（与原版的差异，已登记）：
    原版把记忆拼进 system prompt 并做 thread 级冻结；本项目在 ``before_model``
    里插入一条 ``name="memory_injection"`` 的 HumanMessage，并打上 pinned 标记——
    这样第 14 章的折叠会跳过它（pinned 不折叠），效果等价且离线可断言。
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage

from workagentharness.context.compaction_state import pin_message
from workagentharness.memory.entities import EntityRef
from workagentharness.memory.extract import extract_facts, should_persist_long_term
from workagentharness.memory.injection import format_memory_for_injection
from workagentharness.memory.store import MemoryStore

MEMORY_MESSAGE_NAME = "memory_injection"


class MemoryRuntimeMiddleware(AgentMiddleware):
    """跑一轮：读记忆注入 → 模型回答 → 抽取事实写库。"""

    def __init__(
        self,
        store: MemoryStore,
        *,
        thread_id: str,
        entity: EntityRef | None = None,
        inject: bool = True,
    ) -> None:
        super().__init__()
        self.store = store
        self.thread_id = thread_id
        self.entity = entity or EntityRef("user", "local-user")
        self.inject = inject
        # 同一 thread 只注入一次：每轮重拼没有意义，还会把上下文越堆越长
        self._injected_threads: set[str] = set()

    # ---------- 注入 ----------
    def before_model(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        if not self.inject or self.thread_id in self._injected_threads:
            return None
        facts = self.store.facts(entity=self.entity, limit=50)
        block = format_memory_for_injection(facts)
        if not block:
            return None
        message = HumanMessage(content=block, name=MEMORY_MESSAGE_NAME)
        pin_message(message)
        self._injected_threads.add(self.thread_id)
        return {"messages": [message]}

    # ---------- 巩固 ----------
    def after_model(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        messages = list(state.get("messages") or [])
        last_user = next((m for m in reversed(messages) if getattr(m, "type", "") == "human"), None)
        if last_user is None:
            return None
        text = str(getattr(last_user, "content", "") or "")
        candidates = extract_facts(text)
        for candidate in candidates:
            self.store.add_task_note(self.thread_id, "user", candidate.content)
            if should_persist_long_term(candidate):
                self.store.add_fact(
                    candidate.content,
                    category=candidate.category,
                    confidence=candidate.confidence,
                    entity=self.entity,
                )
        return None

    # ---------- 收尾 ----------
    def clear_thread(self) -> int:
        """任务结束清理短期记忆（对齐原版 ``clear_task_memory``）。"""
        self._injected_threads.discard(self.thread_id)
        return self.store.clear_task_memory(self.thread_id)


__all__ = ["MEMORY_MESSAGE_NAME", "MemoryRuntimeMiddleware"]
