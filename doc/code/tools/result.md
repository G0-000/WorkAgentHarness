# tools/result.py — 工具结果标准协议

> **源码路径**: `backend/packages/harness/workagentharness/tools/result.py`
> **对应功能**: WAH-TOOL-002

## 顺序执行链

```text
工具函数返回字符串 / shape_result(...)
  │
  ▼ 1. truncate_text(content, MAX_RESULT_CHARS=8000)
  ├─ 长度 ≤ 8000 → 原样返回，truncated=False
  ├─ 长度 > 8000 → 保留头部 + 末尾注明原文总长度，truncated=True
  │
  ▼ 2. shape_result(tool_name, ok, content, error_code, metadata)
  ├─ metadata 注入 {"tool": tool_name, ...}
  └─ 返回 ToolResult(ok, content, error_code, truncated, metadata)
  │
  ▼ 3. 交给 Agent / 事件流 / UI 消费
  └─ 三方只看同一种结构，不关心具体工具返回类型
```

## ToolResult 字段

| 字段 | 含义 |
|---|---|
| `ok` | 是否成功 |
| `content` | 给模型看的文本（已截断） |
| `error_code` | 稳定错误类别（`InvalidExpression` / `PathNotAllowed` / `Timeout`），不含异常原文 |
| `truncated` | 内容是否被截断 |
| `metadata` | 结构化附加信息（工具名、行数、耗时等） |

## 关键设计

1. **统一收敛**：无论工具内部返回 int、dict 还是异常，出口都是 `ToolResult`，上层不用写类型分支。
2. **截断不是丢弃**：超长内容保留头部，并明确标注"原文共 N 字符"，模型知道还有内容没看到。
3. **错误类别而非原文**：`error_code` 用稳定字符串，避免把异常栈、路径、密钥片段带进上下文。

## 边界与待补

- 无大结果引用（`large_result_store`）：截断后没有"按需再取"通道
- 无按工具类型差异化截断（读文件、搜索结果、命令输出应各有上限）
- 无结构化 metadata 的白名单校验（当前直接合并任意 dict）
