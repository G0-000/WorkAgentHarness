# 第 3 篇｜让 Agent 会用工具、会流式交付

这是独立仿写教程册的一篇。先按本页准备，再逐章打开教程。每章都要求从 EvoFlow 真实调用链出发，在 WorkAgentHarness 做最小闭环，然后补入口、状态、功能和边界。

## 开始条件
完成上篇出口；可跳过掌握内容，但需做本篇综合练习。

1. 冻结本篇实际使用的三仓库 commit 与工作区状态。
2. 浏览本篇关联功能 ID，在唯一功能清单更新本篇学习项。
3. 每章先完成源码阅读和调用链证据，再写实现；不要先复制目录。
4. 每章结尾记录真实入口、fake 依赖、未完成项与对下一章的依赖。

## 本篇章节

**主线四章（8 / 9 / 11 / 12）串成一条可运行链路**，第 10 章（后台命令）是扩展与选学，不阻塞主线。

| 章节 | 独立教程 | 小节 | 功能范围 | 定位 |
|---|---|---|---|---|
| 第 8 章 | [工具目录、Schema 与结果协议](8. 工具目录Schema与结果协议.md) | 8.1 / 8.2 | `WAH-TOOL-001–002` | 主线（最小闭环） |
| 第 9 章 | [内置工具、文件/终端和宿主边界](9. 内置工具文件终端和宿主边界.md) | 9.1 / 9.2 | `WAH-TOOL-003–004` | 主线（最小闭环） |
| 第 10 章 | [后台命令、Browser Bridge 与 Computer Use](10. 后台命令BrowserBridge与ComputerUse.md) | 10.1 / 10.2 | `WAH-TOOL-010–011、WAH-TOOL-009` | **扩展 + 选学**：10.1 已实现可跑；10.2 只讲形态、不实现 |
| 第 11 章 | [Middleware、上下文整理与本地调度](11. Middleware上下文整理与本地调度.md) | 11.1 / 11.2 | `WAH-TOOL-005、WAH-TOOL-007–008、WAH-MEM-001、WAH-MEM-008` | 主线（审计已通，折叠/续跑是简化实验） |
| 第 12 章 | [事件、SSE、恢复和界面消费](12. 事件SSE恢复和界面消费.md) | 12.1 / 12.2 | `WAH-TOOL-006、WAH-API-002、WAH-UI-002、WAH-UI-004` | 主线（CLI 消费已通，无独立 HTTP 服务） |
| 第 13 章 | [第3篇综合测试与验收：工具调用与流式交付](13. 第3篇综合测试与验收：工具调用与流式交付.md) | — | `本篇集成` | 已验收（fake 模型真实工具调用） |

## 篇-章-节目录

| 章 | 节（独立文件） | 验收 |
|---|---|---|
| 8 | 8.1 工具目录别名与Schema / 8.2 工具结果协议与截断 | `test_ch08_catalog.py`（7 例） |
| 9 | 9.1 内置计算工具与安全求值 / 9.2 文件工具与宿主边界 | `test_ch09_tools.py`（13 例） |
| 10 | 10.1 后台命令与终端会话 / 10.2 浏览器桥与ComputerUse（无代码） | `test_ch10_background.py`（10.1 共 7 例；10.2 无测试） |
| 11 | 11.1 Middleware调用链与工具审计 / 11.2 上下文预算与自动后续动作 | `test_ch11_middleware.py`（10 例） |
| 12 | 12.1 流事件生产 / 12.2 流式消费与SSE恢复 | `test_ch12_events.py`（10 例） |
| 13 | 13.1 工具闭环 / 13.2 流式交付（分组，无节文件） | `test_ch13_part3_e2e.py`（4 例） |
## 本篇测试

| 项 | 内容 |
|---|---|
| 测试文件 | `test_ch08_catalog.py`(7)、`test_ch09_tools.py`(13)、`test_ch10_background.py`(7)、`test_ch11_middleware.py`(10)、`test_ch12_events.py`(10)、`test_ch13_part3_e2e.py`(4) |
| 用例数 | 51 |
| 覆盖 | 8.1–8.2 目录与截断、9.1–9.2 计算/文件/终端、10.1 后台命令、11.1–11.2 审计与折叠续跑、12.1–12.2 事件与 SSE、13.1–13.2 真实 CLI 闭环 |
| 不覆盖 | 10.2 浏览器桥（本仓无实现代码，无测试，不得记为已实现） |
| 重跑 | `uv run --project packages/harness python tests/run_chapter_tests.py 8 9 10 11 12 13` |

## 本篇已落地的代码

| 模块 | 文件 | 作用 |
|---|---|---|
| 工具目录 | `tools/catalog.py` | `ToolCatalog`：注册、别名解析、`schemas()` / `describe_all()` |
| 结果协议 | `tools/result.py` | `ToolResult` + `truncate_text(limit=MAX_RESULT_CHARS)` |
| 内置工具 | `tools/builtins/calculator.py` | AST 白名单安全求值（**本项目自造，原版无对应**） |
| 内置工具 | `tools/builtins/workspace_file.py` | `read_text_file` / `list_directory`，**只读**，`resolve_in_workspace` 做路径边界 |
| 终端工具（扩展） | `tools/host_direct/terminal_tool.py` | 危险命令正则、前台超时、后台分离、输出截断 |
| 终端会话（扩展） | `tools/host_direct/terminal_session.py` | `ThreadShellState`：线程级 cwd 与输出缓冲 |
| 中间件 | `middleware/tool_audit.py` | `ToolAuditMiddleware`：工具调用耗时与结果规模 |
| 中间件 | `middleware/context_compaction.py` | 上下文折叠：`MAX_CONTEXT_CHARS=12000`、`KEEP_RECENT_MESSAGES=6` |
| 中间件 | `middleware/goal_auto_continue.py` | 自动续跑：`MAX_STEPS=8`，计数存**进程内** `_STEPS` |
| 事件 | `events/stream.py` | LangGraph chunk → 稳定事件 |
| 事件 | `events/sse.py` | `encode_sse_event` / `EventBuffer(maxlen=200)` / `sse_event_stream` |
| 响应层 | `app_server/sse.py` | `build_sse_response` / `create_sse_app`（Starlette，**不提供独立 HTTP 进程**） |
| 编排 | `execution/run_service.py` | `execute` / `execute_stream` 生命周期 |
| 入口 | `cli/main.py` | 工具装配 + `--stream` + `--sse` 消费 |

## 本篇未落地（明确标注，不伪造）

| 项 | 状态 | 原因 / 边界 |
|---|---|---|
| 浏览器桥 / Computer Use（`WAH-TOOL-011`） | 不实现 | 原版在 `app/gateway/routers/`，本项目无网关层；10.2 只做形态对照 |
| ZCode 工具桥（`WAH-TOOL-009`） | 未接入 | 需要外部工具协议与能力声明 |
| 独立 HTTP 服务 | 不做 | 依赖里没有 fastapi/uvicorn，只到"可挂载的 Starlette app" |
| 事件持久化 | 不做 | `EventBuffer` 是内存 `deque`，重启即丢；补发 ≠ 持久化恢复 |
| goal 状态持久化 | 不做 | `_STEPS` 是进程内 dict，重启归零；与 EvoFlow 的库内 goal 行不同 |
| 写文件能力 | 不做 | 不可逆，需要备份、审批、diff 预览 |
| Web 端渲染（`WAH-UI-002/004`） | 未做 | 只有 CLI 消费与响应层，没有前端 |

## 本篇综合练习（贯穿四章，同一程序逐层加）

**一个请求走完全链路**：用户在 CLI 输入「计算 99*3」→

| 步 | 发生什么 | 对应章节 |
|---|---|---|
| 1 | `ToolCatalog` 把 `calculator` 的 name/description/schema 交给模型 | 8.1 |
| 2 | 模型返回 `tool_calls`，参数 `{"expression": "99*3"}` | 8.1 |
| 3 | 工具执行，结果包成 `ToolResult`，超长则截断 | 8.2 / 9.1 |
| 4 | `ToolAuditMiddleware` 记录这次调用的耗时与结果规模 | 11.1 |
| 5 | `events/stream` 产出 `tool_call` / `tool_result` / `text_delta` | 12.1 |
| 6 | CLI 用 `--stream` 打字机式打印，用 `--sse` 打印协议帧 | 12.2 |

**再做一次失败路径**：输入「计算 `__import__('os').system('ls')`」→ 计算工具应按 AST 白名单拒绝，`tool_result.ok=false`，模型收到错误文本而不是执行结果。这一步同时验证 8.2 的事件判定（`tool_result_ok`）和 9.1 的安全求值。

手工调用内部函数不算端到端。

## 本篇完成标准

- 主线四章（8 / 9 / 11 / 12）的功能 ID 已学习，或在状态清单中写明阻塞/排除理由。
- 至少一个真实用户入口端到端完成上面的贯穿练习（含一次失败路径）。
- 能讲清入口、核心逻辑、状态存储、返回路径与失败处理。
- 代码、记录和图使用同一 WorkAgentHarness commit。
- **第 10 章不计入完成标准**：10.1 属扩展（可选）、10.2 属选学（不实现代码）。
