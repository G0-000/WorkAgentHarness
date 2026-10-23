# execution/run_service.py — Run 编排服务

> **源码路径**: `backend/packages/harness/workagentharness/execution/run_service.py`
> **对应功能**: WAH-RUN-004、WAH-RUN-007

## 顺序执行链

```text
RunService.execute(owner_id, session_id, text)
  │
  ├─► 空文本检查 → raise ValueError
  │
  ├─► runs.start(run_id, session_id, owner_id, now)    # run → running
  │
  ▼ try:
  │
  ├─► sessions.add_message(session_id, "user", text)
  │
  ├─► agent.invoke(
  │     {"messages": [("user", text)]},
  │     {"configurable": {"thread_id": session_id}},
  │   )
  │
  ├─► sessions.add_message(session_id, "assistant", answer)
  │
  └─► runs.complete(run_id, now)
        return RunResult(status="completed", answer=...)
  │
  ▼ except KeyboardInterrupt:
  ├─► runs.cancel(run_id, now)
  └─► raise
  │
  ▼ except Exception:
  ├─► error_code = type(exc).__name__    # 只存类型，不存内容
  ├─► runs.fail(run_id, error_code, now)
  └─► return RunResult(status="failed", error_code=...)
```

## 关键设计

1. **状态包裹**：整个 Agent 调用包在 try/except 里，保证 run 一定走到终态，不卡 running。
2. **错误脱敏**：只记录异常类型名（如 `RuntimeError`），不记录错误消息内容，避免敏感信息入库。
3. **两套历史**：业务 messages 表（可查询）和 LangGraph checkpoint（Agent 恢复状态）分开存。

## 边界与待补

- KeyboardInterrupt 只标记状态，不真正中断 Agent 内部的模型调用
- 无流式输出（整轮 invoke 完才返回）
- 无并发 run 控制
- 无断连 / 重连恢复
