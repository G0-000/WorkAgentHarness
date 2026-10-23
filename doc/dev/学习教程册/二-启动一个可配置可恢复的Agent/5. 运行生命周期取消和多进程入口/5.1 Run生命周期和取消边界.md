# 第 5 章 · 第 1 节｜Run 生命周期和取消边界

## 本节业务问题

一次 Agent 执行是一条 Run。Run 要有唯一 id、明确状态转换、可追踪错误类别和资源关闭逻辑。将 run 标成 cancelled 不等于模型请求、工具或后台任务已经停止。

## 调用流程

```text
validate input → RunRepository.start
 → save user message → Agent.invoke
 → save assistant message → complete
                         ├→ exception → fail
                         └→ KeyboardInterrupt → cancelled + re-raise
```

## 代码解释

- [run_repository.py](../../../../../backend/packages/harness/workagentharness/persistence/run_repository.py)：使用 `WHERE status='running'` 限制一次终态更新。
- [run_service.py](../../../../../backend/packages/harness/workagentharness/execution/run_service.py)：集中编排 Agent 和 repository；失败只保存异常类型，避免把敏感异常文本写入数据库。
- 本实现是同步最小版；消息和 run 不是一个事务，当前取消也没有向模型/工具传递 token。

## 跟着做与验收

验证 completed、failed、cancelled 各一条 run；尝试重复终态写入必须失败。然后实现可传播 cancellation token，证明耗时调用确实停止，并验证断连、重复请求、进程退出和资源释放。只看数据库 status 不算取消验收。
