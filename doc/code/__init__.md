# WorkAgentHarness 代码文档总览

> 本文档按源码模块组织，解释每个文件的职责、调用链和设计取舍。
> 功能学习路线见 [学习手册](../dev/学习手册/README.md)；功能状态见 [功能清单](../dev/学习手册/功能清单.md)。

## 模块地图

| 模块 | 职责 | 对应功能 ID |
|---|---|---|
| [config/](config/) | YAML 配置加载、环境变量展开、字段校验 | WAH-RUN-001 |
| [models/](models/) | 模型工厂：从配置构造 fake / openai-compatible ChatModel | WAH-RUN-002 |
| [agents/lead_agent/](agents/lead_agent/) | Lead Agent 构造：模型 + 系统提示 + checkpointer 组装 | WAH-RUN-003 |
| [agents/checkpointer/](agents/checkpointer/) | SQLite Checkpoint 持久化 | WAH-RUN-005 |
| [persistence/](persistence/) | 业务库 schema、Session / Run Repository | WAH-RUN-006、WAH-RUN-007 |
| [execution/](execution/) | RunService：编排 Agent 调用、消息写入、状态流转 | WAH-RUN-004、WAH-RUN-007 |
| [cli/](cli/) | CLI 入口：解析参数、装配依赖、交互循环 | WAH-RUN-008 |
| [app_server/](app_server/) | stdio JSON-RPC 子集：initialize / ping / turn/start | WAH-API-009 |

## 主调用链

```text
CLI 入口 (cli/main.py)
  │
  ├─► config.loader.load_chat_model_config()     # 读 YAML + env 展开 + 校验
  │
  ├─► persistence.db.open_database()             # 业务 SQLite 建表
  │
  ├─► agents.checkpointer.provider.open_checkpointer()  # Checkpoint SQLite
  │
  ├─► models.factory.create_chat_model()         # 构造 LLM
  │
  ├─► agents.lead_agent.make_lead_agent()        # 组装 Agent
  │
  └─► execution.run_service.RunService.execute()   # 跑一次对话
        │
        ├─► runs.start()                         # run 状态 → running
        ├─► sessions.add_message("user", ...)    # 写用户消息
        ├─► agent.invoke({thread_id})            # LangGraph 执行
        ├─► sessions.add_message("assistant", ...) # 写助手回复
        └─► runs.complete()                       # run 状态 → completed
```
