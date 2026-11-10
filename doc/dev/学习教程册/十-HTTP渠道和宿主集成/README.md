# 第 10 篇｜HTTP、渠道和宿主集成

这是独立仿写教程册的一篇。**本篇是设计文档篇：只写方案、不实现代码。**

## 开始条件

完成第九篇出口（MCP/插件/Skills/A2A 的设计方案已写完）。

1. 在唯一功能清单里确认 `WAH-API-001~010`、`WAH-AUTO-005` 的当前状态。
2. **先认清一个前提**：本项目第三篇已核实**只有 starlette，没有 fastapi / uvicorn**，所以本篇三章都**不具备实现前提**。

## 本篇定位

| 事实 | 说明 |
|---|---|
| 代码进度 | 停在第三篇。本篇四章（含篇末验收章）**没有实现代码** |
| 已有基础 | `app_server/sse.py:32 build_sse_response` / `:43 create_sse_app`（能构造响应，不启动服务）；`events/sse.py` 全套编码 |
| 本篇主题 | "终端里能跑的东西，怎么让浏览器/别的客户端也能用" |
| 最大的跨度 | 引入一个**常驻进程**和一个**新依赖**（uvicorn），这是本项目第一次 |

## 本篇章节

| 章节 | 独立教程 | 功能范围 | 状态 |
|---|---|---|---|
| 第 44 章 | [Gateway 启动、依赖和聊天 API](44. Gateway启动依赖和聊天API.md) | `WAH-API-001–002、WAH-API-008` | 设计完成，未实现 |
| 第 45 章 | [Gateway 兼容协议、语音和 OpenAI/LangGraph 代理](45. Gateway兼容协议语音和OpenAILangGraph代理.md) | `WAH-API-003–004、WAH-API-010` | 设计完成，未实现 |
| 第 46 章 | [渠道适配器、消息总线与渠道状态](46. 渠道适配器消息总线与渠道状态.md) | `WAH-API-005–007、WAH-AUTO-005` | 设计完成，未实现 |
| 第 47 章 | [第10篇综合测试与验收：HTTP渠道与宿主集成](47. 第10篇综合测试与验收：HTTP渠道与宿主集成.md) | `本篇集成` | 未学习，仅验收设计 |

## 本篇三条澄清

1. **`app_server/` 只有 3 个文件**：`chat_bridge.py`、`embed.py`、`stdio_rpc.py`。它专注"桥"（`_auth_headers:61`、`_build_stream_url:130`、`_parse_sse_frame:153`），**不是完整 HTTP 框架**。完整 Gateway 在别处。
2. **渠道适配器在原版 harness 里不存在**。`grep -rln "channel_adapter\|ChannelAdapter\|MessageBus"` 无有效命中；`feishu/wecom` 只出现在 `proactive/` 的**出站推送**（`feishu_notify.py:34 _approval_channels`、`:39 _feishu_channel_not_opted_out`、`:75 resolve_role_feishu_target`）。双向渠道（用户发消息进来）**不在本仓**。第 46 章因此是"按设计写"，不是仿写。
3. **兼容协议省的是"改客户端"的成本**。`platform/isolated_loop.py:14 run_coroutine_on_fresh_loop(coro)` 说明嵌入场景有"已在事件循环里"的坑——不能直接 `asyncio.run`。

## 本篇综合练习（文档级，不跑代码）

场景：一个只认 OpenAI 格式的客户端，要接上你的 Agent。

1. 客户端发的 `messages` 怎么变成内部消息？
2. `stream=true` 时，内部 `token` 事件怎么变成 `choices[].delta.content`？
3. 内部报错怎么映射成 OpenAI 的 `{error:{message,type}}`？
4. 如果这个客户端还发了 `tools` 参数，你支持吗？
5. 这个方案要新增哪个依赖？对现有 CLI 有没有影响？

五问写表，最后一列填"本项目现实（能做/不能做/为什么）"。

## 本篇出口

能解释"从 CLI 到浏览器，中间缺哪几样东西，以及缺它们各自的代价"。
