# app_server/ — stdio JSON-RPC 服务端

> **源码路径**: `backend/packages/harness/workagentharness/app_server/`
> **对应功能**: WAH-API-009 App Server 本地协议

## 文件清单

| 文件 | 职责 |
|---|---|
| `stdio_rpc.py` | 逐行读取 stdin JSON-RPC 请求，执行后写 stdout 响应 |
