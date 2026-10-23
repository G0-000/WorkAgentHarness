# cli/main.py — CLI 装配与入口

> **源码路径**: `backend/packages/harness/workagentharness/cli/main.py`
> **对应功能**: WAH-RUN-008

## 顺序执行链

```text
main()
  │
  ▼ 1. 解析参数
  ├─► argparse
  │   --config   默认 config.yaml
  │   --db       默认 data/workagentharness.db
  │   --thread   继续已有 session
  │   --once     单轮模式
  │   --mode     cli / app-server
  │
  ▼ 2. 装配依赖
  ├─► load_chat_model_config(args.config)
  ├─► open_database(args.db)
  ├─► open_checkpointer(args.db)
  ├─► create_chat_model(chat_config)
  ├─► make_lead_agent(model, checkpointer=saver)
  ├─► SessionRepository(database)
  ├─► RunRepository(database)
  └─► RunService(agent, sessions, runs)
  │
  ▼ 3. 启动模式
  ├─► mode=app-server → serve_stdio(service, sessions)
  │
  └─► mode=cli
        ├─► sessions.create(session_id, owner_id)
        ├─► --once → 单轮执行后退出
        └─► 交互循环 → input() 等待用户输入
              /exit /quit 退出，空行跳过
  │
  ▼ finally:
  ├─► checkpoint_conn.close()
  └─► database.close()
```

## 关键设计

1. **统一装配**：所有依赖都在 main() 里组装好，传给 RunService；业务逻辑不关心调用来源。
2. **owner_id 硬编码**：当前所有请求都是 `local-user`，鉴权在后续治理篇补。
3. **finally 关闭连接**：不管正常退出还是异常，都释放数据库连接。

## 边界与待补

- 无子命令（只有一个主入口）
- 无配置校验错误的友好提示
- 无日志输出
