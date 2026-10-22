# EvoFlow 功能全景与源码查漏

> 这份盘点把产品文档、真实入口、后端核心、路由、客户端和发布形态放在同一张范围图中，供课程分篇查漏。它不是“目录数 = 功能数”的结论。每个用户行为仍须落到[功能单元路线](功能单元路线.md)中的稳定 ID，并在[功能清单](功能清单.md)写真实调用者和验收证据。

## 基准快照和盘点范围

当前本地 EvoFlow `main` 与 `origin/main` 同步，快照为 `87a957720b74c7e68b0e22fab9c79a9291f62b17`；AgentFlow 第一遍基线为 `d39429698752ce01770896c2be887d2ca952cb2b`；WorkAgentHarness 当前基线请在开章时运行 `git rev-parse HEAD`。课程和清点记录必须标注当时 commit。

EvoFlow 根目录未找到 AGENTS 指引中提到的 `.codebasewiki/index/index.md` 和 `architecture.md`。本次源码导航改用仓库根 `README.md`、`backend/ARCHITECTURE.md`、用户文档、实际入口/注册、测试和运行时调用链。缺少知识库索引作为资料缺口登记，不用旧图上的行号替代当前证据。

本地快照需逐项检查的范围：

1. `backend/packages/harness/evoflow/`：51 个一级核心包。
2. `backend/app/gateway/`：73 个 Python 路由模块（含内部自检和包入口）；应用层另有事件、流式、语音、v4、依赖和启动装配。
3. `backend/app/channels/`：25 个渠道及 bus/manager/service/model 文件。
4. `evopanel/src/`、`evopanel/src-tauri/`、`evopanel/e2e/`：Web 页面、React/ZCode、桌面 IPC/权限和端到端场景。
5. `skills/`、`docker/`、`backend/packaging/`、`scripts/`、`docs/user/`：随产品提供的技能、部署/打包、运维工具和用户行为说明。

文件数量只用于说明本次检查面和重复执行清点；每个新快照应重跑清点。数量不代表功能完成度，也不能直接作为章节数。

## 从用户行为看完整产品

| 产品功能域 | 用户能做什么 | 课程篇章 | 主要功能 ID |
|---|---|---|---|
| 启动、配置和对话 | 配模型/凭证，开始和继续多轮对话，查看回复 | 第一篇 | `WAH-RUN-001–009` |
| 工具执行和结果交付 | 让 Agent 发现/调用工具，流式查看进度，恢复中断结果 | 第二篇 | `WAH-TOOL-001–009`、`WAH-API-002`、`WAH-UI-002/004` |
| 上下文、记忆和资产 | 跨轮次带入上下文、维护记忆与资产/产物 | 第三篇 | `WAH-MEM-001–008` |
| 文档知识和代码索引 | 上传、检索、引用文档，检索代码符号 | 第四篇 | `WAH-KNOW-001–007` |
| 委派和受限执行 | 子代理执行任务，在 sandbox/审批/权限下操作 | 第五篇 | `WAH-EXEC-001–007`、`WAH-GOV-008` |
| 计划与长任务 | Plan/Goal、协作账本、Workflow、探索、暂停恢复 | 第六篇 | `WAH-PLAN-001–009` |
| 自动化和主动运行 | 定时执行、Heartbeat、主动任务和通知 | 第七篇 | `WAH-AUTO-001–006` |
| 扩展生态 | MCP、插件、Skills、社区 Provider、外部 Agent/A2A | 第八篇 | `WAH-EXT-001–010` |
| API、消息渠道和宿主 | HTTP/SSE、v4/语音、IM 渠道、本地 App Server | 第九篇 | `WAH-API-001–009` |
| 身份、安全、运维 | 身份与 ACL、组织/许可、审批、Trace/Eval | 第十篇 | `WAH-GOV-001–008`、`WAH-OBS-001–006` |
| 完整用户产品 | Web/Desktop、ZCode、设置、任务和语音操作 | 第十一篇 | `WAH-UI-001–011` |
| 集成及快照覆盖 | 上述能力从真实入口协作，完成差异收口 | 第十二篇 | 引用全部适用 ID，不新增重复 ID |

这是产品行为导航，不表示所有目录中的实现都已经形成用户可见功能。逐个 ID 需要找真实 caller；找不到时应记录为内部支撑、孤立实现、未接线或待核实。

## 51 个核心包如何进入课程

以下包清单按当前源码中的一级目录核对。子目录继续在对应章节按具体行为拆分；同一包可被多章引用，一个包不必然等于一个用户功能。

| 功能群 | 核心包 | 课程归属和核对重点 |
|---|---|---|
| 配置、模型与运行时 | `config`、`models`、`agents`、`core`、`runtime`、`session_execution`、`session_tool_binding`、`cancellation`、`persistence`、`cli`、`app_server`、`platform`、`utils` | 第一、二篇；核验启动注册、调用者、状态与单向 app/core 边界 |
| 工具、宿主执行与安全 | `tools`、`scheduler`、`sandbox`、`execution_security` | 第二、五、七篇；逐个 builtin 和 host-direct 工具核对权限、真实执行路径及工具调度消费者 |
| 记忆与用户资产 | `context`、`memory`、`assets`、`artifacts`、`items`、`reflection` | 第三篇；区分对象所有者、生命周期、召回/注入调用链和真实消费端 |
| 知识和代码检索 | `knowledge`、`uploads`、`code_index` | 第四篇；上传→解析→索引→检索→引用→Agent/UI 消费逐段核验 |
| 子代理、计划和任务协作 | `subagents`、`plans`、`collab`、`workflows`、`stage`、`exploration`、`exploration_graph` | 第五、六篇；分清内部子代理、跨 Agent 协作、计划、Workflow 和探索组件 |
| 自动化和主动任务 | `automation`、`proactive` | 第七篇；分清一次性 automation、持久定时调度和持续主动循环 |
| 外部扩展和互操作 | `mcp`、`plugins`、`skills`、`capability`、`community`、`external_agents`、`a2a` | 第八、九篇；核对发现、安装、信任、授权、运行、卸载和真实调用方 |
| 身份、组织与管理 | `authz`、`organizations`、`guardrails`、`license`、`admin`、`webui` | 第十篇；建立入口×身份×资源×动作保护矩阵，验证 UI/API 都受保护 |
| 观测、诊断和评估 | `observability`、`debug`、`eval` | 第十篇；区分已存储日志与真实查询/展示的证据 |

上表覆盖当前 51 个一级包：`a2a`、`admin`、`agents`、`app_server`、`artifacts`、`assets`、`authz`、`automation`、`cancellation`、`capability`、`cli`、`code_index`、`collab`、`community`、`config`、`context`、`core`、`debug`、`eval`、`execution_security`、`exploration`、`exploration_graph`、`external_agents`、`guardrails`、`items`、`knowledge`、`license`、`mcp`、`memory`、`models`、`observability`、`organizations`、`persistence`、`plans`、`platform`、`plugins`、`proactive`、`reflection`、`runtime`、`sandbox`、`scheduler`、`session_execution`、`session_tool_binding`、`skills`、`stage`、`subagents`、`tools`、`uploads`、`utils`、`webui`、`workflows`。

## 应用层入口必须逐个查

课程里的 Gateway/API、channels 和应用层功能不能仅靠核心包清单覆盖。当前 `backend/app/gateway/routers/` 的模块名全部纳入入口盘点：

```text
_tools_selftest.py, a2a.py, agents.py, apps.py, apps_debug.py, artifacts.py, assets.py,
auth.py, automation_scheduler.py, background_bash.py, browser_bridge.py, browser_embed.py,
browser_snapshots.py, browser_stream.py, channels.py, chat_sessions.py, client_presence.py,
client_trace.py, collab.py, cua_bridge.py, custom_env_settings.py, debug_agent_trace.py,
debug_stream_paint.py, diagnostics.py, errors.py, eval.py, events.py, goal.py,
hang_diagnostics.py, identity.py, items.py, knowledge.py, knowledge_owned.py,
langgraph_proxy.py, license.py, mcp.py, mcp_server.py, media_assets.py, media_settings.py,
meetings.py, memory.py, models.py, observability.py, openai_compat_apps.py, organizations.py,
panel_settings.py, plans.py, platform.py, platform_config.py, plugins.py, runs.py,
runtime_paths.py, security_settings.py, session_notifications.py, sessions.py, share.py,
skills.py, speech.py, stage_news.py, stream_resume.py, suggestions.py, task_memory.py,
tasks.py, threads.py, tool_approval_settings.py, tools.py, ui_extensions.py, uploads.py,
usage.py, web_search_settings.py, webui.py, workspaces.py
```

路由文件是盘点起点。对每个有用户行为的路由，记录 HTTP 方法/路径、router include/启动注册、身份与权限依赖、请求/响应 schema、服务调用、持久化、错误码、相关测试以及 UI/外部调用者。 `_tools_selftest.py`、debug、demo 或兼容代理等模块要判定为维护/诊断/产品接口，不能只因文件名有 route 就算用户核心能力。

### 路由到课程功能的归属

下面的映射覆盖上方列出的每一个路由模块。一个模块可服务多个行为；章节里仍要逐 endpoint 查真实调用方。无独立用户行为的 diagnostics/debug/demo/selftest 路由归诊断或内部支撑，不单独虚增功能。

| 路由组 | 路由模块 | 功能 ID / 课程章节 |
|---|---|---|
| 对话、运行、thread、分享和连接状态 | `chat_sessions`、`sessions`、`threads`、`runs`、`session_notifications`、`share`、`client_presence`、`events`、`stream_resume`、`suggestions` | `WAH-RUN-004–007/010`、`WAH-TOOL-006`、`WAH-API-002`、`WAH-OBS-002`；第 3–5、10、35、43 章 |
| Agent、Goal、Plan、任务、协作、App、Workflow、Stage | `agents`、`goal`、`plans`、`tasks`、`collab`、`meetings`、`apps`、`apps_debug`、`stage_news`、`automation_scheduler` | `WAH-RUN-003`、`WAH-PLAN-001–011`、`WAH-AUTO-001–006`；第 3、22–30 章 |
| 工具、后台进程、浏览器、CUA、宿主和 workspace | `tools`、`tool_approval_settings`、`background_bash`、`browser_bridge`、`browser_embed`、`browser_snapshots`、`browser_stream`、`cua_bridge`、`runtime_paths`、`workspaces`、`_tools_selftest` | `WAH-TOOL-001–004/010–011`、`WAH-EXEC-003–007`、`WAH-KNOW-006–007`；第 6–8、18、21、46 章 |
| 知识、上传、记忆和用户资产 | `knowledge`、`knowledge_owned`、`uploads`、`memory`、`task_memory`、`assets`、`artifacts`、`items` | `WAH-KNOW-001–005/008`、`WAH-MEM-001–007`、`WAH-PLAN-011`；第 11–17、23、44 章 |
| 媒体资产和设置 | `media_assets`、`media_settings` | `WAH-MEDIA-001`、`WAH-UI-005–006`；第 33、44、46 章 |
| MCP、插件、技能、互操作和 UI 扩展 | `mcp`、`mcp_server`、`plugins`、`skills`、`a2a`、`ui_extensions` | `WAH-EXT-001–011`；第 31–34、44 章 |
| HTTP/兼容协议和渠道 | `speech`、`openai_compat_apps`、`langgraph_proxy`、`channels` | `WAH-API-003–007/010`、`WAH-AUTO-005`；第 30、33、36–37、46 章 |
| 身份、配置、组织、License 和安全 | `auth`、`identity`、`organizations`、`license`、`platform`、`platform_config`、`custom_env_settings`、`panel_settings`、`security_settings`、`web_search_settings` | `WAH-GOV-001–007`、`WAH-RUN-001`、`WAH-UI-005`；第 2、38–40、44 章 |
| Trace、错误、日志、用量、诊断和评估 | `client_trace`、`debug_agent_trace`、`debug_stream_paint`、`diagnostics`、`errors`、`hang_diagnostics`、`observability`、`eval`、`usage` | `WAH-OBS-001–007`、`WAH-UI-004/006`；第 10、41–44 章 |

### 渠道代码文件核对表

`backend/app/channels/` 当前相关 Python 文件为：

```text
base.py, channel_io_log.py, dingtalk.py, dingtalk_registration.py, feishu.py,
feishu_automation_learned_chat.py, feishu_message_format.py, feishu_registration.py,
feishu_stream_bridge.py, manager.py, message_bus.py, models/goal.py, service.py,
services/goal_context_compressor.py, services/goal_service.py, slack.py,
sse_feishu_bridge.py, store.py, telegram.py, wecom.py, wecom_registration.py,
wecom_setup.py, weixin.py, weixin_registration.py, weixin_setup.py
```

分别标注协议 adapter、注册/config、消息格式、Goal/automation 特例、持久化、bus/manager 和 stream bridge 的职责；对 Feishu、Weixin、DingTalk、Slack、WeCom、Telegram 按当前快照逐一确认启用状态。对应 `WAH-API-005–007`、`WAH-AUTO-005` 和第 30/37 章。

`backend/app/channels/` 逐项核对 `base.py`、`manager.py`、`message_bus.py`、`service.py`、`store.py`、`channel_io_log.py`、`models/`、`services/` 和渠道 adapter/registration。当前包含 DingTalk、Feishu、Slack、Telegram、WeCom、Weixin 相关模块；必须从各自注册与启动路径验证哪些真正启用，以及消息是否真实经过 bus/manager。

## Web、桌面和发版范围

| 检查面 | 当前源码入口 | 必须覆盖的行为 |
|---|---|---|
| Web 启动/路由/聊天 | `evopanel/src/boot/`、`react/`、`pages/chat-react.js`、路由/注册表 | 首次启动、登录、深链/刷新、请求、事件流、错误、历史恢复 |
| 页面和设置 | `evopanel/src/pages/`、`components/` | Agent、Apps、资产、渠道、知识、任务、计划、设置、License、组织、观测/Eval、资源市场逐页绑定后端行为 |
| ZCode 子系统 | `evopanel/src/zcode-ui/`、`zcode-shared/`、`zcode-rpc/`、`zcode-services/`、`zcode-provider/`、`zcode-provider-node/`、`zcode-model-option-map/` | UI/RPC/服务/provider 契约、错误、权限、桌面与 Web 复用边界 |
| 桌面端 | `evopanel/src-tauri/src/`、`capabilities/`、`permissions/`、`commands/` | IPC allowlist、命令/文件/窗口权限、进程管理、更新、日志、语音快捷入口 |
| 端到端验证 | `evopanel/e2e/`、`backend/tests/` | 识别真实端到端用例及依赖真假；对未覆盖场景补 WorkAgentHarness 验收，不以组件测试代替产品旅程 |
| 部署和发行 | `docker/`、`backend/packaging/`、`evopanel/src-tauri/`、根 `scripts/`、`RELEASE.md` | 开发/生产启动、平台差异、资源打包、升级/卸载、签名、失败回滚和安全默认值 |

当前 `evopanel/src/pages/` 的 84 个页面/模块入口也全部纳入页面复核（其中一部分是页面共用组件、说明页或诊断页，并非独立用户功能）：

```text
AssetCenterContent.tsx, about-update.js, about.js, agent-trace-compaction.js, agent-trace-field-glossary.js,
agent-trace-format.js, agent-trace-i18n.js, agent-trace-invocation-kinds.js,
agent-trace-json-modal.js, agent-trace-model-response.js, agent-trace-obs-sqlite.js,
agent-trace-system-prompt.js, agent-trace.js, agents-role-ui.js, agents-shared.js, agents.js,
apps-detail.js, apps-history.js, apps-run.js, apps.js, assets.js, bench-dual-session-perf.js,
bench-stream-perf.js, channels.js, chat-react.js, cron.js, expert-center-shared.js, expert.js,
extensions.js, general.js, items.js, knowledge-detail.js, knowledge-owned-activity.js,
knowledge-owned-hub.jsx, knowledge-owned-placeholders.js, knowledge-owned-reader.jsx,
knowledge-owned.js, knowledge-owned.jsx, knowledge.js, license-keys.js, login.js,
mail.js, mobile-me.js, models.js, operations.js, premium-activate.js, proactive-employee.js,
proactive-run.js, proactive-work-board.js, proactive.js, project-detail.js, projects.js,
settings.js, settings/UsageCodeIndexPanel.tsx, settings/code-index.js, settings/env.js,
settings/evoflow-bridge-services.ts, settings/hub.js,
settings/installed-packs.js, settings/license.js, settings/media.js,
settings/mcp-server-management.tsx, settings/meta.js,
settings/my-resources.js, settings/plans.js, settings/remote.js, settings/resource-market.js,
settings/plugin-management.tsx, settings/resources.js, settings/security.js,
settings/shortcuts.js, settings/sso.js,
settings/usage.js, settings/users.js, settings/web-search.js, share-view.js, skills.js,
system-logs.js, task-detail-workbench.js, task-detail.js, tasks.js, tools.js,
ui-extension-shell.js, workflow.js
```

此外还要检查 `evopanel/src/react/`、`components/`、`zcode-*`、`voice-overlay/`、路由表、boot 流程及 `src-tauri/`。页面文件逐一归到第 41–46 章和 `WAH-UI`/相关 API ID；有页面但没有后端调用、只在 Desktop 可用、由第三方模块提供、或仅供诊断的情况必须在功能清单注明。

客户端页面数量或打包脚本数量会变化；逐章从导航入口及后端 API 反向核对，发现新页面或发行模式时先补到对应功能 ID，再更新课程。Bench、debug、迁移、维护脚本等可能是开发工具而不是终端产品能力，需要记录分类结论。

## 仓库级用户能力与文档

- `skills/` 下仓库自带 Skills：要逐个检查清单、元数据、安装/加载、注入工具或 Agent 的方式和许可；它和 `evoflow/skills/` 的技能运行能力是两个层面。
- `community/` 下 Provider：搜索、抓取、媒体等能力按具体目录登记 provider、配置、注册、消费方、失败降级与来源引用；不能用一个“community 已实现”概括。
- `docs/user/` 是产品行为佐证，不是源码证据。按 quick-start、chat、configuration、tasks、security、integration、cases 等主题与 route/UI 交叉验证，发现文档承诺而没有实现的行为登记差异。
- `docker/`、installer/packaging 和发布脚本：只把终端用户实际需要的启动、升级、数据位置、安全配置作为产品功能；仅维护者使用的脚本作为工程范围登记。

## 盘点关闭方法

完成某一篇前，逐项确认：

1. 本篇功能 ID 均有 EvoFlow 路径/符号、真实入口或“未找到入口”的结论、调用者、相关配置/迁移/测试/用户文档证据。
2. 本篇覆盖到的核心包和 Gateway route 文件已归入功能 ID 或明确标注内部支撑、诊断/维护入口、孤立实现或排除。
3. 所有有用户界面的功能都有 API/事件映射；所有有 API 的用户能力都知道调用方；跨层桥接有启动注册证据。
4. 关键行为按课程中的 L1→L4 顺序在 WorkAgentHarness 实现或作有证据的差异说明；实际状态写回唯一功能清单。
5. 更新快照时，重新枚举包、route、channel、UI/Tauri 和发布入口，再对比上一版差异；不要直接复制本页数量和旧路径。

若发现无法映射的行为，先创建稳定 `WAH-<域>-NNN`，补入[功能单元路线](功能单元路线.md)并分配章节，再继续实现。功能全景只有在所有源码入口及用户文档承诺都可追到 ID 或有依据分类后，才能称为“本快照范围已盘点”；不代表 WorkAgentHarness 已实现这些功能。
