# config/model_config.py — 模型配置契约

> **源码路径**: `backend/packages/harness/workagentharness/config/model_config.py`
> **对应功能**: WAH-RUN-001、WAH-RUN-002

## 职责

定义 `ChatModelConfig` 数据类，是配置层和模型工厂之间的类型契约。

## 数据结构

```python
@dataclass(frozen=True)
class ChatModelConfig:
    provider: str          # "fake" / "openai-compatible"
    model: str             # 模型名
    base_url: str = ""     # OpenAI 兼容 API 地址
    api_key: str = ""      # 凭证
    temperature: float = 0.2
```

## 关键设计

1. **frozen=True**：配置一旦加载就不可变，防止运行期意外修改。
2. **不包含运行时状态**：只存配置项，不持有 model 实例 / 连接池。
3. **最小字段集**：只覆盖当前最小闭环需要的，后续补 max_tokens / top_p / timeout 等。

## 边界与待补

- 无 per-agent 配置覆盖
- 无模型路由（多 provider  fallback）
- 无成本 / 限流配置
