# events/stream.py — 流事件生产

> **源码路径**: `backend/packages/harness/workagentharness/events/stream.py`
> **对应功能**: WAH-TOOL-006、WAH-API-002

## 顺序执行链

```text
RunService.execute_stream(...)
  │
  ▼ 1. stream_agent_run(agent, [("user", text)], thread_id=...)
  │
  ▼ 2. agent.stream(inputs, config, stream_mode=["messages","updates"])
  │
  ├─ mode == "messages"
  │    ├─ chunk = (message_chunk, metadata)
  │    ├─ AIMessage / AIMessageChunk 且 content 非空
  │    └─ yield {"type": "text_delta", "text": ...}
  │
  └─ mode == "updates"
       └─ {节点名: {"messages": [新消息...]}}
            ├─ AIMessage 且带 tool_calls
            │    └─ 每个 call → yield {"type": "tool_call", "name", "args"}
            └─ ToolMessage
                 ├─ content 以 "[" 开头 → ok=False
                 └─ yield {"type": "tool_result", "name", "ok"}
```

## 事件类型

| 事件 | 字段 | 谁产生 |
|---|---|---|
| `run_start` | `run_id`、`thread_id` | RunService（不是本模块） |
| `text_delta` | `text` | 本模块（messages 模式） |
| `tool_call` | `name`、`args` | 本模块（updates 模式） |
| `tool_result` | `name`、`ok` | 本模块（updates 模式） |
| `run_end` | `status`、`answer` / `error_code` | RunService（不是本模块） |

## 关键设计

1. **协议翻译层**：前端不解析 LangGraph 内部结构（节点名、消息对象、metadata），只消费稳定事件字典。
2. **生命周期分层**：`run_start` / `run_end` 归 `RunService`，避免一次运行出现两个结束事件。
3. **工具结果不下发原文**：只发 `name` 和 `ok`，防止大段工具输出把 UI/SSE 塞爆。

## 边界与待补

- 无节点级 `step_start/step_end`
- 无 token 用量（usage）事件
- 无 interrupt / resume 事件
- 无断线恢复游标（客户端重连不能续播）
- fake 模型不产生逐 token 流（真实 provider 才有）
