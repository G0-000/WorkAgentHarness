# 第 12 篇｜Web、桌面和 ZCode 产品体验

这是独立仿写教程册的一篇。**本篇是设计文档篇：只写方案、不实现代码。**

## 开始条件

完成第十一篇出口（身份/护栏/组织/观测/Eval 的设计方案已写完）。

1. 在唯一功能清单里确认 `WAH-UI-001~011`、`WAH-TOOL-009` 的当前状态。
2. **认清前提**：原版 Web 层依赖 **FastAPI**（`webui/static.py:71 mount_evopanel_static(app: FastAPI)`），本项目**没有 fastapi / uvicorn**；Tauri **不在 Python 包里**。本篇四章基本不具备实现前提。

## 本篇定位

| 事实 | 说明 |
|---|---|
| 代码进度 | 停在第三篇。本篇五章（含篇末验收章）**没有实现代码** |
| 已有基础 | 有会话与消息三表（能存），但**无列表 API、无搜索、无 UI** |
| 本篇主题 | "用户真正看到的那个界面，需要后端提供什么" |
| 与前几篇的关系 | 第十篇讲协议、第十一篇讲治理，本篇讲**产品形态** |

## 本篇章节

| 章节 | 独立教程 | 功能范围 | 状态 |
|---|---|---|---|
| 第 55 章 | [Web 启动、聊天、会话与历史](55. Web启动聊天会话与历史.md) | `WAH-UI-001–004` | 设计完成，未实现 |
| 第 56 章 | [设置、Agent、知识、任务与管理页面](56. 设置Agent知识任务与管理页面.md) | `WAH-UI-005–006、WAH-AUTO-006、WAH-KNOW-008、WAH-PLAN-010–011、WAH-MEDIA-001` | 设计完成，未实现 |
| 第 57 章 | [ZCode UI、RPC、服务和 Provider 系统](57. ZCodeUIRPC服务和Provider系统.md) | `WAH-TOOL-009、WAH-UI-007–009` | 设计完成，未实现 |
| 第 58 章 | [Tauri、桌面权限、语音和发布安装](58. Tauri桌面权限语音和发布安装.md) | `WAH-API-004、WAH-UI-010–011` | 设计完成，未实现 |
| 第 59 章 | [第12篇综合测试与验收：Web桌面与产品体验](59. 第12篇综合测试与验收：Web桌面与产品体验.md) | `本篇集成` | 未学习，仅验收设计 |

## 本篇三条澄清

1. **原版 Web 层依赖 FastAPI，本项目没有**。`webui/` 五文件（`auth.py`、`middleware.py`、`oidc.py`、`oidc_config.py`、`static.py`）。本项目只有 `starlette`，**不提供独立 HTTP 服务**（第三篇已核实）。所以要老实写"数据层有、产品层无"。
2. **管理页看似都是 CRUD，真正的差别在三处**：名称校验（`admin/agents.py:36 _validate_agent_name` + `:43 _normalize_agent_name` 两步）、错误分类（`admin/errors.py` 三个子类：`NotFoundError` / `ConflictError` / `ValidationError`）、列表/详情分离（`admin/skills.py:20 _skill_row(skill, *, detail=False)`）。**这三处才是能对齐的部分**，页面本身不做。
3. **Tauri 不在本仓**。Python 包里能核实的只有 4 个后端侧符号：`app_server/embed.py:17 resolve_app_server_listen_port`、`:28 resolve_gateway_base_url_for_embed`、`platform/isolated_loop.py:14 run_coroutine_on_fresh_loop`、`platform/asyncio_windows.py`。别把 Tauri 的 Rust 代码当成本仓内容。

## 本篇综合练习（文档级，不跑代码）

场景：用户打开浏览器，点了昨天的会话，想搜"上周问过的财报"。

1. 页面要加载哪几类资源？（静态、列表、搜索、流）
2. "公开路径"和"分享路径"为什么是两种语义？
3. 会话搜索和消息搜索各查什么？
4. 管理页里"新建 Agent"要过几道校验？
5. 桌面版比网页版多要什么权限？后端要做什么适配？

五问写表，最后一列填"本项目：有 / 无 / 有但未接"。

## 本篇出口

能解释"一个 Web/桌面产品形态，后端要提供哪几层，而本项目现在停在哪一层"。
