"""凭证加载与脱敏：密钥只从环境变量进入，日志和错误信息不打印明文。

对应 EvoFlow ``models/credential_loader.py`` 与 ``models/credential_sanitize.py``
的简化版。WorkAgentHarness 的密钥来源约定：

    ``${WORKAGENT_MODEL_API_KEY}``（config.yaml 引用）→ 运行时环境变量。
    配置对象里不允许出现字面量密钥。

提供三个能力：
    1. ``resolve_api_key`` —— 从配置或环境变量取密钥，优先环境变量。
    2. ``mask_api_key`` —— 脱敏显示，只保留前 4 / 后 4 位。
    3. ``sanitize_error`` —— 把异常消息里的疑似密钥替换为占位符。
"""

from __future__ import annotations

import os
import re

from workagentharness.config.model_config import ChatModelConfig

# 与 config/loader.py 的 ${ENV} 展开保持一致：密钥一律走环境变量。
ENV_API_KEY = "WORKAGENT_MODEL_API_KEY"

# 常见密钥长度下限（OpenAI 风格 sk-... 一般远长于此）；低于下限不脱敏。
_MIN_SECRET_LEN = 8


def resolve_api_key(config: ChatModelConfig) -> str:
    """返回实际使用的 API Key：环境变量优先，其次配置值。

    配置里可能已经是 loader 展开后的字面量（来自 ${ENV}），也可能是空串。
    """
    env_key = os.getenv(ENV_API_KEY, "").strip()
    if env_key:
        return env_key
    return (config.api_key or "").strip()


def mask_api_key(key: str) -> str:
    """脱敏显示：``sk-abcdefgh1234`` → ``sk-a****1234``。"""
    if not key:
        return ""
    if len(key) <= _MIN_SECRET_LEN:
        return "*" * len(key)
    return f"{key[:4]}****{key[-4:]}"


# 匹配常见的 sk- 开头密钥片段，用于异常消息脱敏（尽力而为，不追求完美）。
_SK_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{8,}")


def sanitize_error(message: str) -> str:
    """把异常消息里的疑似密钥替换为占位符，避免密钥进入日志/终端。"""
    return _SK_PATTERN.sub("[REDACTED]", message or "")
