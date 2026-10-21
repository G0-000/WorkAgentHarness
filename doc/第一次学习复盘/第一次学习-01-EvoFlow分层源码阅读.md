# M0 记录 01：EvoFlow 分层源码阅读

阅读日期：2026-10-20。源码快照：EvoFlow `v1.1.2` / `b9def02fc84d21a4e38f422e8e66525d481dfd5d`。本记录用于 WorkAgentHarness 第二次学习；AgentFlow 是第一遍实现的复盘样本，不是当前目标仓库。

架构图：[EvoFlow M0：源码分层与 Runtime Port](diagrams/M0-evoflow-layers-20261020-185709/M0-evoflow-layers.html)。图的每个关键节点都带有 EvoFlow 源码证据。Archify 的 showcase 校验、严格检查、浏览器检查均通过；另生成 1440×900 和 2048×1320 的亮/暗主题预览并检查了 1440×900 亮色图，Runtime Port 回连路由清楚，没有遮挡主调用链。

## 已核实的源码事实

| 事实 | 源码证据 | 学习解释 |
|---|---|---|
| EvoFlow 后端分为应用层 `backend/app` 和核心包 `backend/packages/harness/evoflow`。应用层承载 Gateway HTTP、SSE、channels；核心层承载域逻辑和持久化能力。 | `backend/ARCHITECTURE.md:11-24` | 阅读功能时先辨别它是进程/协议接入，还是可独立复用的核心能力。 |
| 依赖原则是 app → core；core 不直接依赖 app。核心需要应用能力时，通过核心定义的 port，由应用层 adapter 在启动时注册。 | `backend/ARCHITECTURE.md:26-30`；`backend/packages/harness/evoflow/runtime/ports.py:1-16`；`backend/app/gateway/runtime_adapters.py:1-10` | Runtime Port 是明确的依赖反转边界，不是让核心任意导入 Gateway 的豁免。 |
| Gateway app 启动时会注册运行时适配器，然后挂载路由；路由注册入口连接到 EvoFlow 核心能力。 | `backend/app/gateway/app.py:142-148,196-211`；`backend/app/gateway/router_registry.py:62-80` | “模块存在”不等于已接线；需要沿启动装配和调用点追踪。 |
| 核心持有共享 SQLite 访问入口。 | `backend/packages/harness/evoflow/persistence/db.py:1-27` | 继续盘点时应追迁移、表/模型、读写者和恢复路径，不能只记数据库文件名。 |
| EvoPanel 的启动入口导入应用 shell/router 和 API state；Tauri 与 Web 的 API transport 按运行方式区分。 | `evopanel/src/main.js:2-18`；`evopanel/src/lib/tauri-api.js:31-64` | 前端图里的“Web / Tauri”是两种传输/宿主路径，不意味着后端部署形态完全相同。 |
| R1 规则目前存在 grandfathered 历史违规。 | `backend/ARCHITECTURE.md:49-57` | 不可把规范目标误写成现状已零违规；后续要把例外映射到具体功能和调用链。 |

## 从源码读出的调用骨架

1. 用户通过 EvoPanel 的 Web 或 Tauri 界面发起交互。
2. Gateway 应用承载 HTTP/SSE/渠道入口，并在启动阶段注册应用侧运行时 adapter。
3. Gateway 路由调用 EvoFlow 核心包；核心通过自身定义的 Runtime Port 请求被允许的应用侧能力。
4. 核心的数据持久化入口汇总到 SQLite 访问层。

这只是当前分层和桥接机制的骨架，不代表所有功能域或所有 Gateway/渠道路径都已在这张图中展开。当前 R1 规则也仍有历史例外。

## 对 WorkAgentHarness 的设计约束

- WorkAgentHarness 当前仍无实现代码；不得把这张 EvoFlow 现状图当成新项目架构已经实现。
- 在 M0 完成域盘点前，不照抄 AgentFlow 第一版的目录或双包骨架。
- 为新项目决定 core/app 边界时，逐项记录为何放入该层、谁负责装配、核心如何访问外部能力。
- 后续每一条功能矩阵记录应继续附 EvoFlow 入口/调用证据、AgentFlow 第一版对照，以及 WorkAgentHarness 的设计或实现状态。

## 下一步问题

- Gateway 的启动装配、渠道收发和用户请求中，哪些路径最终进入 core？哪些仍由应用层直接处理？
- `runtime.ports` 每个 port 的调用方、注册方、生命周期和未注册行为是什么？
- SQLite 的 schema/migration、恢复和后台任务由哪些功能域负责？
- Web、Tauri、CLI、IM 各入口如何到达同一核心能力？

下一步沿上述入口建立 M0 全量功能矩阵稳定 ID；这份分层记录不构成 M0 完成验收。
