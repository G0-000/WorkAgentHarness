# models/resolver.py — 模型解析

> **源码路径**: `backend/packages/harness/workagentharness/models/resolver.py`
> **对应功能**: WAH-RUN-002

## 顺序执行链

```text
resolve_effective_config(config, runtime_model=None, runtime_provider=None)
  │
  ▼ 1. 解析 provider（优先级从上到下，取第一个非空）
  ├─► runtime_override 参数
  ├─► 环境变量 WORKAGENT_MODEL_PROVIDER
  └─► config.provider
  │
  ▼ 2. 解析 model（优先级从上到下，取第一个非空）
  ├─► runtime_override 参数
  ├─► 环境变量 WORKAGENT_MODEL_NAME
  └─► config.model
  │
  ▼ 3. 全部为空 → ValueError
  │
  └─► 返回新的 ChatModelConfig（覆盖合并后的有效配置）
```

## 关键设计

1. **单一事实来源**：模型选择集中在这里，factory 只消费结果，不做第二套判断。
2. **两级阶梯**：WorkAgentHarness 当前是「运行时覆盖 > 配置默认」，对应 EvoFlow resolver 阶梯的前两级；后续可扩展 agent / primary / models[0]。
3. **返回新配置对象**：`ChatModelConfig` 是 frozen dataclass，覆盖不修改原对象。

## 边界与待补

- 无 AgentConfig 层（EvoFlow 的 agent_code 查找）
- 无全局 primary_model / models[0] 回退
- 无解析日志 / 来源标注
