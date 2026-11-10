# 第 2 篇｜启动一个可配置、可恢复的 Agent

这是独立仿写教程册的一篇。先按本页准备，再逐章打开教程。每章都要求从 EvoFlow 真实调用链出发，在 WorkAgentHarness 做最小闭环，然后补入口、状态、功能和边界。

## 开始条件
先完成导学第 1 章

1. 冻结本篇实际使用的三仓库 commit 与工作区状态。
2. 浏览本篇关联功能 ID，在唯一功能清单更新本篇学习项。
3. 每章先完成源码阅读和调用链证据，再写实现；不要先复制目录。
4. 每章结尾记录真实入口、fake 依赖、未完成项与对下一章的依赖。

## 路径约定

- 教程中 EvoFlow 核心包路径（如 `config/model_config.py`、`agents/lead_agent/`）均相对 EvoFlow 仓库的 `backend/packages/harness/evoflow/`。
- `backend/app/...` 是 EvoFlow 仓库根目录下的应用层路径，不属于上面的核心包目录。
- AgentFlow 第一遍核心包路径均相对 AgentFlow 仓库的 `backend/packages/harness/agentflow/`。
- WorkAgentHarness 路径均相对本仓库根目录；例如 `backend/packages/harness/workagentharness/`。
- 阅读前先在本篇[验收记录](验收记录.md)确认源码快照，避免把更新后的路径当作旧版本证据。

## 本篇代码运行入口

本篇的可运行实现位于仓库 `backend/`，要求 Python 3.12 或更高版本。默认配置使用 fake 模型，不需要 API Key。

```bash
cd backend
uv sync --project packages/harness
uv run --project packages/harness workagentharness --once "你好"
```

保存输出中的 thread id 后，可再次指定它检查同一 thread 的 checkpoint 恢复（把 `<thread-id>` 换成上一步真实打印的十六进制串；**尖括号只是占位，不要连尖括号一起复制**，否则会被 shell 当成重定向）：

```bash
uv run --project packages/harness workagentharness --thread <thread-id> --once "再发一条消息"
```

用 stdio JSON-RPC 子集验证本地 App Server 入口：

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize"}' \
  '{"jsonrpc":"2.0","id":2,"method":"turn/start","params":{"text":"你好"}}' \
  | uv run --project packages/harness workagentharness --mode app-server
```

App Server 当前只实现 `initialize`、`server/ping`、`turn/start` 三个学习用方法，不代表与 EvoFlow 协议完整兼容；取消、流式事件、并发执行和桌面宿主桥接属于后续补齐范围。

## 本篇章节

| 章节 | 独立教程 | 功能范围 |
|---|---|---|
| 第 3 章 | [配置、模型供应商与凭证](3. 配置模型供应商与凭证.md) | `WAH-RUN-001–002` |
| 第 4 章 | [Agent 构建、角色与单轮执行](4. Agent构建角色与单轮执行.md) | `WAH-RUN-003–004` |
| 第 5 章 | [消息、会话、Checkpoint、Run 与分享](5. 消息会话CheckpointRun与分享.md) | `WAH-RUN-005–006、WAH-RUN-010` |
| 第 6 章 | [运行生命周期、取消和多进程入口](6. 运行生命周期取消和多进程入口.md) | `WAH-RUN-007–009、WAH-API-009` |
| 第 7 章 | [第2篇综合测试与验收：配置到恢复全链路](7. 第2篇综合测试与验收：配置到恢复全链路.md) | 本篇集成结果 + 各章结果引用 |

本篇当前验收状态见[篇 01 验收记录](验收记录.md)。

## 篇-章-节目录

| 章 | 节（独立文件） | 验收 |
|---|---|---|
| 3 | 3.1 配置契约和配置加载 / 3.2 凭证边界与密钥脱敏 / 3.3 模型工厂与 Fake 行为 | `test_ch03_config.py`（7 例） |
| 4 | 4.1 Agent构造与角色提示 / 4.2 单轮执行与结果返回 | `test_ch04_agent.py`（4 例） |
| 5 | 5.1 会话和业务消息存储 / 5.2 Checkpoint与Thread恢复 / 5.3 分享生命周期（未实现） | `test_ch05_persistence.py`（5 例；5.3 无测试） |
| 6 | 6.1 Run生命周期和取消边界 / 6.2 CLI和stdio-App-Server | `test_ch06_lifecycle.py`（8 例） |
| 7 | 7.1 单轮与恢复 / 7.2 参数与失败路径（分组，无节文件） | `test_ch07_part2_e2e.py`（4 例） |
## 本篇测试

| 项 | 内容 |
|---|---|
| 测试文件 | `test_ch03_config.py`(7)、`test_ch04_agent.py`(4)、`test_ch05_persistence.py`(5)、`test_ch06_lifecycle.py`(8)、`test_ch07_part2_e2e.py`(4) |
| 用例数 | 28 |
| 覆盖 | 3.1–3.3 配置与工厂、4.1–4.2 装配与 thread、5.1–5.2 三表与 checkpoint、6.1–6.2 状态机与 stdio、7.1–7.2 CLI 全链路 |
| 不覆盖 | 5.3 分享生命周期（本仓未实现）；脱敏函数无独立断言（随 3.2 人工核对） |
| 重跑 | `uv run --project packages/harness python tests/run_chapter_tests.py 3 4 5 6 7` |

## 本篇综合练习
挑一个核心用户行为，从真实入口串联本篇已完成能力。先验证成功路径，再制造一个失败情景，观察持久化状态和用户反馈。手工调用内部函数不算端到端。

## 本篇完成标准
- 所有本篇功能 ID 已学习，或在状态清单中写明阻塞/排除理由；“有代码”不能记为已验收。
- CLI 与 stdio App Server 至少各完成一次端到端调用；fake 和真实模型边界如实记录。
- 能讲清入口、核心逻辑、状态存储、返回路径与失败处理。
- 代码、记录和图使用同一 WorkAgentHarness commit。
- 只有 `WAH-RUN-001–009`、`WAH-API-009` 的完整功能出口都通过后，才关闭本篇并开始下一篇；当前教程实现的是可运行基础，不把未实现的完整协议和边界包装成已完成。
- `WAH-RUN-010`（分享生命周期）本意是**独立扩展**，状态停在"待盘点"：5.3 只定义行为与验收，代码、表、路由都不存在，**不作为本篇关闭条件**。
