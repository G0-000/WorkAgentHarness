# 第 3 篇｜让 Agent 会用工具、会流式交付

这是独立仿写教程册的一篇。先按本页准备，再逐章打开教程。每章都要求从 EvoFlow 真实调用链出发，在 WorkAgentHarness 做最小闭环，然后补入口、状态、功能和边界。

## 开始条件
完成上篇出口；可跳过掌握内容，但需做本篇综合练习。

1. 冻结本篇实际使用的三仓库 commit 与工作区状态。
2. 浏览本篇关联功能 ID，在唯一功能清单更新本篇学习项。
3. 每章先完成源码阅读和调用链证据，再写实现；不要先复制目录。
4. 每章结尾记录真实入口、fake 依赖、未完成项与对下一章的依赖。

## 本篇章节

| 章节 | 独立教程 | 小节 | 功能范围 | 状态 |
|---|---|---|---|---|
| 第 6 章 | [工具目录、Schema 与结果协议](6. 工具目录Schema与结果协议.md) | 6.1 / 6.2 | `WAH-TOOL-001–002` | 最小闭环 |
| 第 7 章 | [内置工具、文件/终端和宿主边界](7. 内置工具文件终端和宿主边界.md) | 7.1 / 7.2 | `WAH-TOOL-003–004` | 最小闭环 |
| 第 8 章 | [后台命令、Browser Bridge 与 Computer Use](8. 后台命令BrowserBridge与ComputerUse.md) | 8.1 / 8.2 | `WAH-TOOL-010–011、WAH-TOOL-009` | 待设计（仅边界与验收） |
| 第 9 章 | [Middleware、上下文整理与本地调度](9. Middleware上下文整理与本地调度.md) | 9.1 / 9.2 | `WAH-TOOL-005、WAH-TOOL-007–008、WAH-MEM-001、WAH-MEM-008` | 部分实现（审计已通） |
| 第 10 章 | [事件、SSE、恢复和界面消费](10. 事件SSE恢复和界面消费.md) | 10.1 / 10.2 | `WAH-TOOL-006、WAH-API-002、WAH-UI-002、WAH-UI-004` | 部分实现（CLI 流式已通） |

## 本篇已落地的代码

| 模块 | 文件 | 作用 |
|---|---|---|
| 工具目录 | `tools/catalog.py` | 注册、别名、schema、交给 Agent |
| 结果协议 | `tools/result.py` | `ToolResult` + 8000 字符截断 |
| 内置工具 | `tools/builtins/calculator.py` | AST 白名单安全求值 |
| 内置工具 | `tools/builtins/workspace_file.py` | 只读文件 + 工作区边界 |
| 中间件 | `middleware/tool_audit.py` | 工具调用审计（耗时/结果规模） |
| 事件 | `events/stream.py` | LangGraph chunk → 稳定事件 |
| 编排 | `execution/run_service.py` | `execute_stream` 流式生命周期 |
| 入口 | `cli/main.py` | 工具装配 + `--stream` 消费 |

## 本篇未落地（明确标注，不伪造）

- 后台命令 / 终端会话（WAH-TOOL-010）
- 浏览器桥 / Computer Use（WAH-TOOL-011）
- ZCode 工具桥（WAH-TOOL-009）
- 上下文预算、裁剪、压缩（WAH-TOOL-007、WAH-MEM-001/008）
- 自动后续动作（WAH-TOOL-008）
- SSE 端点、断线恢复、Web 端渲染（WAH-API-002 剩余、WAH-UI-002/004）

## 本篇综合练习
挑一个核心用户行为（建议：用户在 CLI 里说"计算 99*3"，Agent 调工具并流式回传），从真实入口串联本篇已完成能力。先验证成功路径，再制造失败情景（非法表达式、路径越界），观察持久化状态和用户反馈。手工调用内部函数不算端到端。

## 本篇完成标准
- 所有本篇功能 ID 已学习，或在状态清单中写明阻塞/排除理由。
- 至少一个真实用户入口端到端完成本篇场景。
- 能讲清入口、核心逻辑、状态存储、返回路径与失败处理。
- 代码、记录和图使用同一 WorkAgentHarness commit。
