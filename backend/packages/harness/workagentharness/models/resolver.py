"""模型解析：把“用哪个模型”的决策集中到一处。

对应 EvoFlow ``models/resolver.py``。WorkAgentHarness 当前只有一个
``models.chat`` 配置项，没有 EvoFlow 的 runtime override → agent → primary →
models[0] 阶梯；这里先实现前两级，留出后续扩展点：

    1. 运行时覆盖（环境变量 / 调用方显式指定）
    2. 配置默认（``ChatModelConfig.model``）
"""

from __future__ import annotations

import os

from workagentharness.config.model_config import ChatModelConfig

# 运行时覆盖模型名的环境变量；优先级高于配置文件。
ENV_MODEL_OVERRIDE = "WORKAGENT_MODEL_NAME"

# 运行时覆盖 provider 的环境变量；优先级高于配置文件。
ENV_PROVIDER_OVERRIDE = "WORKAGENT_MODEL_PROVIDER"


def resolve_model_name(
    config: ChatModelConfig,
    *,
    runtime_override: str | None = None,
) -> str:
    """按优先级解析最终模型名。

    优先级：``runtime_override`` > ``WORKAGENT_MODEL_NAME`` > 配置 ``model``。
    解析结果为空时抛错，避免把空模型名传给供应商。
    """
    for candidate in (runtime_override, os.getenv(ENV_MODEL_OVERRIDE), config.model):
        text = (candidate or "").strip()
        if text:
            return text
    raise ValueError("未配置模型名：请设置 config.yaml 的 models.chat.model")


def resolve_provider(
    config: ChatModelConfig,
    *,
    runtime_override: str | None = None,
) -> str:
    """按优先级解析最终 provider。

    优先级：``runtime_override`` > ``WORKAGENT_MODEL_PROVIDER`` > 配置 ``provider``。
    """
    for candidate in (runtime_override, os.getenv(ENV_PROVIDER_OVERRIDE), config.provider):
        text = (candidate or "").strip()
        if text:
            return text
    raise ValueError("未配置模型 provider：请设置 config.yaml 的 models.chat.provider")


def resolve_effective_config(
    config: ChatModelConfig,
    *,
    runtime_model: str | None = None,
    runtime_provider: str | None = None,
) -> ChatModelConfig:
    """把运行时覆盖合并进配置，返回一个新的有效配置对象。

    factory 直接消费这个结果，避免每处调用都手动做一次“覆盖 vs 默认”判断。
    """
    return ChatModelConfig(
        provider=resolve_provider(config, runtime_override=runtime_provider),
        model=resolve_model_name(config, runtime_override=runtime_model),
        base_url=config.base_url,
        api_key=config.api_key,
        temperature=config.temperature,
    )
