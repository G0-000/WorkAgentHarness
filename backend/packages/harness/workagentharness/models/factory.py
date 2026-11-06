"""通过统一 LangChain 接口构造 fake 或真实对话模型。"""

import re
from uuid import uuid4

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI

from workagentharness.config.model_config import ChatModelConfig
from workagentharness.models.credential_loader import resolve_api_key, sanitize_error
from workagentharness.models.resolver import resolve_effective_config


class FakeChatModel(BaseChatModel):
    """不联网的确定性模型，用于验证配置、Agent 接线和 thread 恢复。

    它还额外模拟"模型发起工具调用"：当用户输入形如 ``计算 1+2`` 时，
    返回一条带 tool_calls 的 AIMessage。这样离线环境也能跑通
    第三篇的"模型 → 工具 → 结果回传"完整链路，不必接真实供应商。
    """

    answer: str = "已收到"

    # bind_tools 时记录可用工具名，用于决定"要不要模拟工具调用"
    bound_tool_names: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "workagentharness-fake"

    def bind_tools(self, tools, **kwargs):
        """记录被绑定的工具名，返回带这份记录的模型副本。

        create_agent 装配工具时会调用本方法；伪造行为只依赖这份清单，
        不依赖真实工具对象，便于单元测试。
        """
        names = [getattr(tool, "name", "") for tool in tools if getattr(tool, "name", "")]
        return self.model_copy(update={"bound_tool_names": names})

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        """三种行为：工具结果总结 / 模拟工具调用 / 普通回显。"""
        if not messages:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.answer))])

        last = messages[-1]

        # 行为一：上一条是工具结果 → 把结果回述给用户，结束本轮工具循环
        if last.type == "tool":
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content=f"工具结果：{last.content}"))]
            )

        user_messages = [message for message in messages if message.type == "human"]
        latest_text = str(user_messages[-1].content) if user_messages else ""

        # 行为二：用户说"计算 xxx"且 calculator 已绑定 → 模拟模型发起工具调用
        match = re.match(r"计算\s+(.+)$", latest_text.strip())
        if match and "calculator" in self.bound_tool_names:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(
                content="",
                tool_calls=[{
                    "name": "calculator",
                    "args": {"expression": match.group(1).strip()},
                    "id": f"call_{uuid4().hex[:8]}",
                }],
            ))])

        # 行为三：普通回显，用于验证 checkpoint 是否恢复了历史轮数
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
