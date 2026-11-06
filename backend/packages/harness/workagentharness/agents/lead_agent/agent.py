"""构造一个最小对话 Agent；外部模型、工具、中间件和 Checkpointer 由调用方注入。

第三篇的关键变化：
    之前 ``tools=[]`` —— Agent 只会聊天，不会干活。
    现在 ``tools`` 由调用方传入（来自 ``tools/builtins.default_catalog()``），
    ``middleware`` 传入工具审计中间件。Agent 从此能"决定调用工具 → 拿到结果 →
    继续回答"。
"""

from typing import Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver

DEFAULT_SYSTEM_PROMPT = """
你是 WorkAgentHarness 的助手。
回答要清楚、准确；不知道时明确说明，不要编造事实。
需要计算时调用 calculator 工具；需要看文件时调用文件工具，不要凭记忆猜测文件内容。
""".strip()


def make_lead_agent(
    model: BaseChatModel,
    *,
    tools: Sequence[BaseTool] | None = None,
    middleware: Sequence[AgentMiddleware] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
):
    """组合模型、工具、中间件、提示和持久化状态，返回可调用 Agent。

    参数：
        model:        chat model（fake 或真实供应商）
        tools:        可调用工具列表（来自 ToolCatalog.langchain_tools()）
        middleware:   中间件（如 ToolAuditMiddleware）
        checkpointer: 存档器（LangGraph Checkpointer），用于 thread 恢复
        system_prompt: 角色提示

    为什么默认值是 None 而不是空列表：
        避免"可变默认参数"被多个 Agent 共享；None 时在函数内换成空列表。
    """
    return create_agent(
        model=model,
        tools=list(tools or []),
        middleware=list(middleware or []),
        checkpointer=checkpointer,
        system_prompt=system_prompt,
    )
