# 第 4 章 · 第 2 节｜Checkpoint 与 Thread 恢复

## 本节业务问题

业务消息用于查询和展示；checkpoint 保存图状态，供相同 thread 继续执行。二者的写入者、格式和生命周期不同。

## 调用流程

```text
open_checkpointer(db_path) → SqliteSaver
    → make_lead_agent(checkpointer=saver)
    → agent.invoke(..., configurable.thread_id=session_id)
    → 进程重启后沿用同一 thread_id 继续
```

## 代码解释

- [provider.py](../../../../../backend/packages/harness/workagentharness/agents/checkpointer/provider.py)：持有 SQLite 长连接并初始化 LangGraph saver。
- [agent.py](../../../../../backend/packages/harness/workagentharness/agents/lead_agent/agent.py)：把 checkpointer 注入图构造。
- [run_service.py](../../../../../backend/packages/harness/workagentharness/execution/run_service.py)：每次只提交新用户消息，但使用稳定 `thread_id` 让图读取已有状态。
- fake model 按收到的用户消息数回复，可用于看到 checkpoint 恢复；只有真实重启并复用 SQLite 后仍恢复才算通过。

## 跟着做与验收

发第一条消息，关闭进程，再用原 thread id 发第二条；确认 fake 返回的轮数递增，并检查业务消息表与 checkpoint 分工。再用新 thread id 验证隔离。当前环境缺少 LangGraph 依赖，真实重启恢复尚未执行，因此不能据本节代码宣告通过。
