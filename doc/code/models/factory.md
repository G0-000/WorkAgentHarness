# models/factory.py — 模型工厂与 FakeChatModel

> **源码路径**: `backend/packages/harness/workagentharness/models/factory.py`
> **对应功能**: WAH-RUN-002

## 顺序执行链

```text
create_chat_model(config: ChatModelConfig)
  │
  ├─► config.provider == "fake"
  │     └─► return FakeChatModel()
  │
  ├─► config.provider == "openai-compatible"
  │     └─► return ChatOpenAI(
  │           model=config.model,
  │           base_url=config.base_url or None,
  │           api_key=config.api_key,
  │           temperature=config.temperature,
  │           timeout=30,
  │           max_retries=0,
  │         )
  │
  └─► 其他 provider → raise ValueError
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

1. **统一返回 BaseChatModel**：上层 Agent 不关心具体供应商，只面向 LangChain 接口编程。
2. **max_retries=0**：最小闭环先不做重试，失败直接抛。

## 边界与待补

- 无 provider 自动发现 / 可用模型列表
- 无重试 / 限流 / 退避策略
- 无凭证优先级（env > config > 默认）
- 无日志脱敏
