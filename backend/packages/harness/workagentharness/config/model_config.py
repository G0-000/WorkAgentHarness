"""对话模型的最小配置契约。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChatModelConfig:
    """描述如何连接一个模型；不负责创建模型或记录密钥。"""

    provider: str
    model: str
    base_url: str = ""
    api_key: str = ""
    temperature: float = 0.2

