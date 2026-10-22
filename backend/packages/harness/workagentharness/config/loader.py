"""读取 YAML 配置并在运行时展开环境变量。"""

import os
import re
from pathlib import Path
from typing import Any

import yaml

from workagentharness.config.model_config import ChatModelConfig

_ENV_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")


def _expand_env(value: Any) -> Any:
    """递归展开独占字段的 ``${ENV_NAME}``，其他文本保持原样。"""
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, str):
        match = _ENV_PATTERN.fullmatch(value)
        if match:
            name = match.group(1)
            secret = os.environ.get(name)
            if not secret:
                raise ValueError(f"缺少必需的环境变量: {name}")
            return secret
    return value


def load_chat_model_config(path: str | Path) -> ChatModelConfig:
    """加载 ``models.chat`` 并做最小字段校验。"""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"找不到配置文件: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("配置文件顶层必须是对象")
    models = raw.get("models", {})
    chat = models.get("chat", {}) if isinstance(models, dict) else None
    chat = _expand_env(chat)
    if not isinstance(chat, dict):
        raise ValueError("models.chat 必须是对象")

    try:
        config = ChatModelConfig(**chat)
    except TypeError as exc:
        raise ValueError(f"models.chat 配置字段无效: {exc}") from exc

    if not config.provider.strip():
        raise ValueError("models.chat.provider 不能为空")
    if not config.model.strip():
        raise ValueError("models.chat.model 不能为空")
    if config.provider == "openai-compatible" and not config.api_key:
        raise ValueError("openai-compatible provider 需要 api_key")
    if not 0 <= config.temperature <= 2:
        raise ValueError("models.chat.temperature 必须在 0 到 2 之间")
    return config

