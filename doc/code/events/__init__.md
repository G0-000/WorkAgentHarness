# events/__init__.py — 事件层出口

> **源码路径**: `backend/packages/harness/workagentharness/events/__init__.py`
> **对应功能**: WAH-TOOL-006

## 顺序执行链

```text
外部 import workagentharness.events
  │
  ▼ 1. 从 stream.py 导出
  ├─ Event            # dict[str, Any] 类型别名
  └─ stream_agent_run # 事件生成器
  │
  ▼ 2. 使用方
  ├─ execution/run_service.py → execute_stream 包装生命周期
  └─ cli/main.py              → _execute_stream_and_print 消费打印
```

## 关键设计

- 事件生成器是纯函数式：不写数据库、不改 run 状态，只读 Agent 输出。
- 生命周期（run start/end、消息入库、终态）全部在 `RunService`，事件层不承担副作用。

## 边界与待补

- 无 SSE 编码（`data: {...}\n\n`）
- 无事件版本号 / 序号（客户端无法去重与排序）
- 无背压控制（生产者快、消费者慢时无缓冲策略）
