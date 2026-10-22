"""通过统一 LangChain 接口构造 fake 或真实对话模型。"""

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI

from workagentharness.config.model_config import ChatModelConfig


class FakeChatModel(BaseChatModel):
    """不联网的确定性模型，用于验证配置、Agent 接线和 thread 恢复。"""

    answer: str = "已收到"

    @property
    def _llm_type(self) -> str:
        return "workagentharness-fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        """回显消息数量和最后一条用户消息；可观察 checkpoint 是否恢复历史。"""
        user_messages = [message for message in messages if message.type == "human"]
        latest_text = str(user_messages[-1].content) if user_messages else ""
        response_text = f"{self.answer}（第 {len(user_messages)} 轮）：{latest_text}"
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=response_text))]
        )


def create_chat_model(config: ChatModelConfig) -> BaseChatModel:
    """从类型化配置构造模型；Agent 层不需要知道具体供应商。"""
    if config.provider == "fake":
        return FakeChatModel()
    if config.provider == "openai-compatible":
        return ChatOpenAI(
            model=config.model,
            base_url=config.base_url or None,
            api_key=config.api_key,
            temperature=config.temperature,
            timeout=30,
            max_retries=0,
        )
    raise ValueError(f"不支持的模型 provider: {config.provider}")

