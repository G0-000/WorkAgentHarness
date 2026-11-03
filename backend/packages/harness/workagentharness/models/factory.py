"""通过统一 LangChain 接口构造 fake 或真实对话模型。"""

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI

from workagentharness.config.model_config import ChatModelConfig
from workagentharness.models.credential_loader import resolve_api_key, sanitize_error
from workagentharness.models.resolver import resolve_effective_config


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


def create_chat_model(
    config: ChatModelConfig,
    *,
    runtime_model: str | None = None,
    runtime_provider: str | None = None,
) -> BaseChatModel:
    """从类型化配置构造模型；Agent 层不需要知道具体供应商。

    先经 ``resolve_effective_config`` 合并运行时覆盖，再按 provider 分支实例化。
    真实 provider 的密钥一律来自环境变量；构造失败时异常消息先脱敏再抛出。
    """
    effective = resolve_effective_config(
        config,
        runtime_model=runtime_model,
        runtime_provider=runtime_provider,
    )

    if effective.provider == "fake":
        return FakeChatModel()

    if effective.provider == "openai-compatible":
        try:
            return ChatOpenAI(
                model=effective.model,
                base_url=effective.base_url or None,
                api_key=resolve_api_key(effective),
                temperature=effective.temperature,
                timeout=30,
                max_retries=0,
            )
        except Exception as exc:
            raise ValueError(sanitize_error(str(exc))) from exc

    raise ValueError(f"不支持的模型 provider: {effective.provider}")
