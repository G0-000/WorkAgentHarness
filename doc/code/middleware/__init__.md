# middleware/__init__.py — Middleware 层出口

> **源码路径**: `backend/packages/harness/workagentharness/middleware/__init__.py`
> **对应功能**: WAH-TOOL-005

## 顺序执行链

```text
外部 import workagentharness.middleware
  │
  ▼ 1. 从 tool_audit.py 导出
  └─ ToolAuditMiddleware
  │
  ▼ 2. 使用方
  └─ cli/main.py → make_lead_agent(middleware=[ToolAuditMiddleware()])
```

## 关键设计

- 保持出口最小：当前只有工具审计一个中间件。
- 后续上下文预算（WAH-TOOL-007）、自动后续动作（WAH-TOOL-008）、上下文压缩（WAH-MEM-008）都从这里导出，调用方只加不改。

## 边界与待补

- 无 `before_model` / `after_model` 类中间件
- 无中间件顺序控制（列表顺序即执行顺序，但未显式文档化）
