# app_server/stdio_rpc.py — stdio JSON-RPC 子集

> **源码路径**: `backend/packages/harness/workagentharness/app_server/stdio_rpc.py`
> **对应功能**: WAH-API-009

## 顺序执行链

```text
serve_stdio(service, sessions, owner_id="local-user")
  │
  ▼ 逐行读取 stdin
  ├─► json.loads(line)
  │
  ▼ 协议校验
  ├─► 必须是 JSON 对象
  ├─► jsonrpc 必须是 "2.0"
  ├─► method 是字符串，params 是对象
  │
  ▼ 方法分发
  ├─► "initialize"    → 返回 serverInfo + capabilities
  ├─► "server/ping"    → 返回 {"ok": true}
  ├─► "turn/start"     → 校验 text，调 service.execute()
  └─► 其他             → -32601 未知方法
  │
  ▼ 响应
  ├─► 有 id → 写一行 JSON 响应
  └─► 无 id（notification）→ 不返回
  │
  ▼ 错误处理
  ├─► JSONDecodeError  → -32700 无效 JSON
  ├─► ValueError       → -32602 参数错误
  └─► Exception        → -32603 内部错误（不回显细节）
```

## 支持的方法

| 方法 | 参数 | 返回 |
|---|---|---|
| `initialize` | 无 | serverInfo + capabilities.turnStart |
| `server/ping` | 无 | `{"ok": true}` |
| `turn/start` | `text` (必填), `sessionId` (可选) | sessionId / runId / status / answer / errorCode |

## 关键设计

1. **协议层薄**：只做 JSON 解析和响应封装，业务全部委托给 RunService。
2. **错误不回显细节**：内部异常统一返回"内部错误"，不泄露堆栈 / 密钥。
3. **notification 不响应**：符合 JSON-RPC 规范，无 id 的请求不返回。

## 边界与待补

- 只有三个教学方法，不是完整 EvoFlow App Server 协议
- 无流式事件（SSE / stream chunks）
- 无并发 run / interrupt / cancel 通知
- 无宿主鉴权 / 权限校验
