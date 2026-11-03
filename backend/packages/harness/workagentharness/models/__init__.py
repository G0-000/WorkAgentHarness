"""模型 provider、解析与凭证边界。"""

from workagentharness.models.credential_loader import mask_api_key, resolve_api_key, sanitize_error
from workagentharness.models.factory import FakeChatModel, create_chat_model
from workagentharness.models.resolver import (
    resolve_effective_config,
    resolve_model_name,
    resolve_provider,
)

__all__ = [
    "FakeChatModel",
    "create_chat_model",
    "mask_api_key",
    "resolve_api_key",
    "resolve_effective_config",
    "resolve_model_name",
    "resolve_provider",
    "sanitize_error",
]
