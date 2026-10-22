"""构造一个最小对话 Agent；外部模型和 Checkpointer 由调用方注入。"""

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

DEFAULT_SYSTEM_PROMPT = """
你是 WorkAgentHarness 的助手。
回答要清楚、准确；不知道时明确说明，不要编造事实。
""".strip()


def make_lead_agent(
    model: BaseChatModel,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
):
    """组合模型、提示和可选的持久化状态，返回可调用 Agent。"""
    return create_agent(
        model=model,
        tools=[],
        middleware=[],
        checkpointer=checkpointer,
        system_prompt=system_prompt,
    )

