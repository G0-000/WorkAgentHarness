# models/ — 模型解析、凭证与工厂

> **源码路径**: `backend/packages/harness/workagentharness/models/`
> **对应功能**: WAH-RUN-002 模型选择与凭证

## 包职责

从 `ChatModelConfig` 解析最终有效的 provider/model，安全加载凭证，再构造 LangChain `BaseChatModel` 实例，屏蔽供应商差异。

## 文件清单

| 文件 | 职责 |
|---|---|
| `resolver.py` | 模型/供应商解析：运行时覆盖 > 环境变量 > 配置默认 |
| `credential_loader.py` | 凭证加载与脱敏：密钥只走环境变量，日志/错误不打印明文 |
| `factory.py` | `create_chat_model()` 工厂函数 + `FakeChatModel` 实现 |

## 主调用链

```text
create_chat_model(config, runtime_model=None, runtime_provider=None)
  │
  ├─► resolve_effective_config(config)          # resolver.py
  │     provider: 覆盖 > $WORKAGENT_MODEL_PROVIDER > config.provider
  │     model:    覆盖 > $WORKAGENT_MODEL_NAME > config.model
  │
  ▼ provider 分支
  ├─► fake               → FakeChatModel()
  ├─► openai-compatible  → ChatOpenAI(api_key=resolve_api_key(effective))
  │                          │
  │                          └─ 异常 → sanitize_error(str(exc)) 后抛出
  └─► 其他               → ValueError
```
