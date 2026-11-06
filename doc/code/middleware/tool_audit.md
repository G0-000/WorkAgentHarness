# middleware/tool_audit.py — 工具调用审计中间件

> **源码路径**: `backend/packages/harness/workagentharness/middleware/tool_audit.py`
> **对应功能**: WAH-TOOL-005

## 顺序执行链

```text
create_agent(model, tools, middleware=[ToolAuditMiddleware()])
  │
  ▼ 图编译：middleware 挂到工具节点外层
  │
  ▼ 运行时每次工具调用
  ├─ wrap_tool_call(request, handler)
  │    ├─ tool_name = request.tool_call["name"]
  │    ├─ started = perf_counter()
  │    ├─ logger.info("tool.start name=...")
  │    ├─ result = handler(request)        # 进下一层：其他 middleware 或工具本身
  │    │
  │    ├─ 成功：
  │    │    ├─ elapsed = (perf_counter()-started)*1000
  │    │    ├─ ToolMessage → 记 content_chars
  │    │    └─ 其他类型 → 记 result_type
  │    │
  │    └─ 异常：
  │         ├─ logger.warning("tool.fail name=... error=类型名")
  │         └─ raise（不吞异常，交给 RunService 转 failed）
  │
  └─ 返回 result
```

## 为什么用 middleware 而不是写进工具函数

| 方案 | 问题 |
|---|---|
| 每个工具函数里写日志 | 业务与日志耦合；换日志格式要改所有工具 |
| middleware 统一挂 | 写一次，所有工具生效；工具函数保持纯业务 |

## 关键设计

1. **只观测不改语义**：不吞异常、不改返回值，失败仍由上层 `RunService` 决定终态。
2. **不记异常原文**：只记 `type(exc).__name__`，避免把用户输入、密钥片段写进日志。
3. **耗时单位毫秒**：`perf_counter` 高精度，适合工具级打点。

## 边界与待补

- 只有 `wrap_tool_call`，没有 `before_model` / `after_model`（上下文预算、压缩在中）
- 日志只到标准 logging，未接事件流（UI 的"工具活动"面板需要事件，不是日志）
- 无采样/开关（每次调用都记，高频工具会吵）
- 无审计落库（只写日志，不写数据库）
