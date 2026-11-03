# models/factory.py — 模型工厂

> **源码路径**: `backend/packages/harness/workagentharness/models/factory.py`
> **对应功能**: WAH-RUN-002

## 顺序执行链

```text
create_chat_model(config, runtime_model=None, runtime_provider=None)
  │
  ▼ 1. 合并运行时覆盖
  ├─► resolve_effective_config(config)         # resolver.py
  │     provider = 覆盖 > $WORKAGENT_MODEL_PROVIDER > config.provider
  │     model    = 覆盖 > $WORKAGENT_MODEL_NAME > config.model
  │
  ▼ 2. 按 provider 分支实例化
  ├─► "fake" → FakeChatModel()
  │
  ├─► "openai-compatible" → ChatOpenAI(
  │       model=effective.model,
  │       base_url=effective.base_url or None,
  │       api_key=resolve_api_key(effective),   # credential_loader.py
  │       temperature=effective.temperature,
  │       timeout=30, max_retries=0)
  │     │
  │     ▼ 异常 → sanitize_error(str(exc)) → ValueError
  │
  └─► 其他 → ValueError("不支持的模型 provider: ...")
```

## FakeChatModel 行为

```text
_generate(messages)
  │
  ├─► 过滤所有 human 消息
  ├─► 取最后一条 human 消息内容
  ├─► 统计 human 消息总数
  └─► 返回 "已收到（第 N 轮）：{最后一条用户消息}"
```

- 不调用任何外部 API
- 用途：验证配置加载、Agent 接线、checkpoint 恢复，不需要 API Key

## 关键设计

1. **Agent 依赖 `BaseChatModel`**：工厂把 provider 分支集中在单点，Agent 不需要 import `ChatOpenAI`。
2. **密钥不落代码/日志**：`api_key` 经 `resolve_api_key` 从环境变量解析；构造异常先 `sanitize_error` 脱敏再抛出。
3. **超时/重试策略**：`timeout=30`、`max_retries=0`，让失败容易观察；限流、供应商差异、凭证优先级留待补齐。

## 边界与待补

- 无 provider 自动发现 / 可用模型列表
- 无重试 / 限流 / 退避策略
- 无模型 fallback
- 无请求/响应 payload 记录
