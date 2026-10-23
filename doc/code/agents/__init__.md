# agents/ — Agent 构造与 Checkpoint

> **源码路径**: `backend/packages/harness/workagentharness/agents/`
> **对应功能**: WAH-RUN-003 Agent 图构建、WAH-RUN-005 Checkpoint 与恢复

## 目录结构

```text
agents/
├── lead_agent/
│   └── agent.py        # make_lead_agent()：构造 Lead Agent
└── checkpointer/
    └── provider.py      # open_checkpointer()：SqliteSaver 初始化
```
