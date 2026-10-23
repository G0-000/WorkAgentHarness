# agents/lead_agent/agent.py — Lead Agent 构造器

> **源码路径**: `backend/packages/harness/workagentharness/agents/lead_agent/agent.py`
> **对应功能**: WAH-RUN-003

## 顺序执行链

```text
make_lead_agent(model, checkpointer=None, system_prompt=DEFAULT)
  │
  ▼
  langchain.agents.create_agent(
    model=model,              # BaseChatModel 实例
    tools=[],                 # 当前无工具，篇02 补
    middleware=[],            # 当前无中间件，篇02 补
    checkpointer=saver,       # SqliteSaver 或 None
    system_prompt=system_prompt,
  )
  │
  ▼ 返回 Runnable（编译后的 LangGraph 图）
```

## 关键设计

1. **依赖注入**：model 和 checkpointer 都由调用方传入，本函数不关心具体实现。
2. **空 tools/middleware**：最小闭环先跑通纯对话，工具和中间件在篇02 补。
3. **默认系统提示**：当前只有一段通用助手提示，后续补角色 / 工具说明 / 上下文。

## 边界与待补

- 无多角色 Agent（goal / worker / planner 等）
- 无图结构可视化 / 调试入口
- 无配置驱动的 Agent 组装
