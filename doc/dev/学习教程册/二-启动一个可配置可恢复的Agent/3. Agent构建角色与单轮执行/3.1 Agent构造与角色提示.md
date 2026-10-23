# 第 3 章 · 第 1 节｜Agent 构造与角色提示

## 本节业务问题

模型只负责生成回复；Agent 把模型、角色提示、工具和状态机制组合成可执行图。本篇先用 lead agent 做最小实现，工具和 middleware 留到对应功能单元。

## 调用流程

```text
配置加载 → create_chat_model → make_lead_agent
                              ├─ model
                              ├─ system_prompt
                              ├─ tools=[]
                              ├─ middleware=[]
                              └─ checkpointer（本节可为 None）
```

## 代码解释

- [agent.py](../../../../../backend/packages/harness/workagentharness/agents/lead_agent/agent.py)：`make_lead_agent` 接收已构造模型，而不是在内部解析配置或创建供应商客户端。
- `system_prompt` 单独注入，角色指令与模型参数属于不同配置边界。
- `tools=[]`、`middleware=[]` 是本篇明确的范围选择，不代表 EvoFlow 的 agent 没有工具或 middleware。
- 可选 `checkpointer` 让同一 Agent 构造入口既支持单轮，也支持后续恢复。

## 跟着做

1. 用 fake model 调用 `make_lead_agent`，读清 create_agent 的四类依赖。
2. 只修改系统提示，再发相同输入，区分 prompt 效果和 provider 参数。
3. 对照 EvoFlow `agents/lead_agent/agent.py`，标记 graph 构造、动态 prompt、工具和中间件注入点；不要把 EvoFlow 的完整 lead agent 缩成一个静态 prompt 后就宣称功能等价。

## 本节验收

能画出依赖装配图；替换模型不需修改 Agent 构造函数；说明当前实现为何只覆盖最小角色和提示路径。
