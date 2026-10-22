# 第 5 章 · 第 2 节｜CLI 和 stdio App Server

## 本节业务问题

CLI 与 App Server 是不同输入/输出协议，但应复用同一 `RunService`。CLI 负责命令参数和终端展示；stdio server 负责 JSON-RPC framing 和响应，不直接操作 Agent。

## 调用流程

```text
CLI args ────────────┐
                     ├→ 依赖装配 → RunService → Agent/Repository
JSON-RPC stdin/stdout┘
```

## 代码解释

- [main.py](../../../../../backend/packages/harness/workagentharness/cli/main.py)：装配配置、数据库、checkpointer、Agent 和 service；`--mode` 决定终端 CLI 或 App Server。
- [stdio_rpc.py](../../../../../backend/packages/harness/workagentharness/app_server/stdio_rpc.py)：当前教学子集支持 `initialize`、`server/ping`、`turn/start`，并处理解析/参数/未知方法错误。
- 与 EvoFlow 对照：其 `evoflow/app_server/stdio_rpc.py` 还有 Gateway proxy、stream 通知、`turn/interrupt`、thread 生命周期；当前本地版本并不协议兼容。
- 实际代码保存在上述 `.py` 文件；本节不维护重复副本。

## 跟着做与验收

先按篇 README 运行 CLI，再把同一输入改由 stdio RPC 发送。检查两入口生成的 run 和业务消息一致；测试非法 JSON、未知方法、空文本和 EOF 清理。随后按 EvoFlow 实际协议补齐初始化状态、配置、thread/turn、事件流、interrupt、并发和关闭行为，再连接真实桌面宿主。
