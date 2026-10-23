# models/ — 模型工厂

> **源码路径**: `backend/packages/harness/workagentharness/models/`
> **对应功能**: WAH-RUN-002 模型选择与凭证

## 包职责

从 `ChatModelConfig` 构造 LangChain `BaseChatModel` 实例，屏蔽供应商差异。

## 文件清单

| 文件 | 职责 |
|---|---|
| `factory.py` | `create_chat_model()` 工厂函数 + `FakeChatModel` 实现 |
