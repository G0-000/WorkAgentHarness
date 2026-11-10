# 第 9 篇｜MCP、插件、技能和外部能力生态

这是独立仿写教程册的一篇。**本篇是设计文档篇：只写方案、不实现代码。**

## 开始条件

完成第八篇出口（自动化与主动任务的设计方案已写完）。

1. 在唯一功能清单里确认 `WAH-EXT-001~011`、`WAH-MEDIA-001`、`WAH-TOOL-009` 的当前状态。
2. 本篇四章里有两章是**"原版能力存在但本项目不做"**（第 40、42 章），读的时候要留意差异表。

## 本篇定位

| 事实 | 说明 |
|---|---|
| 代码进度 | 停在第三篇。本篇五章（含篇末验收章）**没有实现代码** |
| 已有基础 | 第三篇的 `ToolCatalog` 只能装内置工具，装不了外部能力 |
| 本篇主题 | "怎么让 Agent 用上自己没写的能力" |
| 四章的分工 | MCP 接工具 / 插件接程序 / Skills 接知识 / A2A 接别的 Agent |

## 本篇章节

| 章节 | 独立教程 | 功能范围 | 状态 |
|---|---|---|---|
| 第 39 章 | [MCP 连接、发现、调用和 OAuth](39. MCP连接发现调用和OAuth.md) | `WAH-EXT-001–003` | 设计完成，未实现 |
| 第 40 章 | [插件、扩展壳、运行桥接与 Capability 授权](40. 插件扩展壳运行桥接与Capability授权.md) | `WAH-EXT-004–005、WAH-EXT-007、WAH-EXT-011` | 设计完成，未实现 |
| 第 41 章 | [Skills、资源市场和 Community Provider](41. Skills资源市场和CommunityProvider.md) | `WAH-EXT-006、WAH-EXT-008、WAH-MEDIA-001` | 设计完成，未实现 |
| 第 42 章 | [外部 Agent Adapter 与 A2A 互操作](42. 外部AgentAdapter与A2A互操作.md) | `WAH-EXT-009–010、WAH-PLAN-004` | 设计完成，未实现 |
| 第 43 章 | [第9篇综合测试与验收：外部能力生态](43. 第9篇综合测试与验收：外部能力生态.md) | `本篇集成` | 未学习，仅验收设计 |

## 本篇三条澄清

1. **MCP 接的是工具，A2A 接的是 Agent**。`mcp/` 17 文件（`client.py:11 build_server_params`、`pool.py:106 looks_like_connection_error`、`oauth.py:26 OAuthTokenManager`）；`external_agents/` + `a2a/` 是另一种东西（`agent_card.py:56 role_to_agent_card`、`adapter.py:62 _create_a2a_task_record`）。前者是"调函数"，后者是"派活给会思考的东西"。
2. **插件的桥鉴权不是可选项**。`plugins/bridge_auth.py:50 get_bridge_token` / `:83 verify_bridge_token(request)` / `:33 _token_file_path` —— token **落文件**、跨进程共享。这套东西的存在前提是"插件跑在独立进程"。本项目插件是同进程 import，**没有桥，也就没有鉴权**——差异表里要写"不能算已对齐"。
3. **skill 是会被执行的文本，所以要扫**。`skills/security.py:56 scan_for_security_issues(content, *, is_code=True)` —— 代码类查危险命令，文档类查注入话术。另外 `loader.py:50 _build_mtime_map` 说明它是按 mtime 判缓存，不是每次重扫。

## 本篇综合练习（文档级，不跑代码）

场景：给 Agent 加三种能力——读 GitHub issue（MCP）、发企业微信（插件）、审合同（Skill）。

1. 三种能力各自怎么"装"？（配置 / 清单 / 文件）
2. 哪一种需要跨进程？（插件）
3. 哪一种需要扫危险内容？（Skill）
4. 哪一种需要 OAuth？（MCP）
5. 本项目能做哪几种？缺的分别是什么前提？

五问写表，最后一列填"缺什么前提才能做"。

## 本篇出口

能解释"工具、插件、技能、外部 Agent 四种外部能力，各自靠什么机制接进来、各自的风险在哪"。
