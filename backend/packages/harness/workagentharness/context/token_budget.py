"""请求级 token 预算估算（对齐 EvoFlow ``context/model_request_token_estimate.py``）。

原版符号与行号（快照 8e462a37）：
    ModelCallOverheadEstimate          ← :37
    estimate_system_prompt_tokens      ← :112
    estimate_bound_tools_tokens        ← :164

为什么学习版不直接抄 tokenizer：
    原版按真实模型分词器算，需要网络或本地 tokenizer 文件；本项目要求
    ``provider: fake``、离线可跑，所以默认用 ``len(text)//3`` 字符近似，
    但接口留成可插拔的，将来接 tokenizer 只换一个函数，不改调用方。
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Iterable

# 默认近似口径：3 个字符 ≈ 1 token（中英混排的经验值，只用于阈值判断）
DEFAULT_CHARS_PER_TOKEN = 3

Estimator = Callable[[str], int]

_estimator: ContextVar[Estimator | None] = ContextVar("token_estimator", default=None)


def default_estimator(text: str) -> int:
    """默认估算：按字符数除以 3，空文本记 0。"""
    stripped = (text or "").strip()
    if not stripped:
        return 0
    return max(1, len(stripped) // DEFAULT_CHARS_PER_TOKEN)


def set_token_estimator(estimator: Estimator | None) -> Any:
    """替换全局估算器（传 None 恢复默认），返回可用于 reset 的 token。"""
    return _estimator.set(estimator)


def reset_token_estimator(token: Any) -> None:
    """恢复上一次估算器，避免测试之间互相污染。"""
    _estimator.reset(token)


def current_estimator_name() -> str:
    """当前估算器标识，写进估算结果便于事后追查口径。"""
    return "custom" if _estimator.get() is not None else "chars//3"


def estimate_tokens(text: str, *, estimator: Estimator | None = None) -> int:
    """估算一段文本的 token 数。

    优先级：显式传入的 estimator > 上下文里的 estimator > 默认字符近似。
    """
    chosen = estimator or _estimator.get() or default_estimator
    return max(0, int(chosen(text or "")))


def _message_text(message: Any) -> str:
    """把任意 LangChain 消息的 content 压成字符串（list 形式也要能算）。"""
    content = getattr(message, "content", "")
    if isinstance(content, list):
        return " ".join(str(part) for part in content)
    return str(content or "")


@dataclass(frozen=True)
class TokenEstimate:
    """一次模型调用的开销拆分（对应原版 ModelCallOverheadEstimate）。"""

    system_tokens: int
    message_tokens: int
    total_tokens: int
    estimator: str

    def to_meta(self) -> dict[str, int]:
        """原版 ``:49 to_meta``：给日志/事件层用的扁平字典。"""
        return {
            "system_tokens": self.system_tokens,
            "message_tokens": self.message_tokens,
            "total_tokens": self.total_tokens,
        }


def estimate_request_tokens(
    messages: Iterable[Any],
    *,
    system_prompt: str = "",
    estimator: Estimator | None = None,
) -> TokenEstimate:
    """估算"这一轮请求"的 token 开销：系统提示 + 全部消息。

    注意：这里不含工具 schema 的 token（原版 ``estimate_bound_tools_tokens`` 另算），
    学习版把工具 schema 视为固定开销，不参与折叠决策。
    """
    system_tokens = estimate_tokens(system_prompt, estimator=estimator)
    message_tokens = sum(
        estimate_tokens(_message_text(message), estimator=estimator) for message in messages
    )
    return TokenEstimate(
        system_tokens=system_tokens,
        message_tokens=message_tokens,
        total_tokens=system_tokens + message_tokens,
        estimator="custom" if estimator is not None else current_estimator_name(),
    )


__all__ = [
    "DEFAULT_CHARS_PER_TOKEN",
    "Estimator",
    "TokenEstimate",
    "current_estimator_name",
    "default_estimator",
    "estimate_request_tokens",
    "estimate_tokens",
    "reset_token_estimator",
    "set_token_estimator",
]
