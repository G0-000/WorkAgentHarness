# EvoFlow 对照台账与差异建议

这份台账是**唯一事实源**：文档里出现的每个文件、类、方法，都必须能在「EvoFlow 真实位置」或「本项目位置」查到。查不到的不许写。

台账建立的直接原因：第三篇 8.1 / 8.2 / 9.2 三节此前写了 9 个不存在的符号（`CommandDecision`、`check_command`、`kill_process_group`、`CommandSession`、`check_site`、`BrowserSession`、`DESTRUCTIVE_ACTIONS`、`ContextBudgetMiddleware`、`ShareRepository`），原因是先写签名再去查原版。规则从这一篇起反向执行：**先查、再写**。

## 使用规则

1. 写代码前先在本台账登记一行：能力 → 原版位置 → 本项目位置 → 状态。
2. 命名跟原版；形态不一致（简化、合并、改写）必须在「差异」列写明。
3. 原版有、本项目不做，标「不实现」并给理由，不写假签名。
4. 与原版有分歧、或认为该改的地方，写进[第五节](#五建议)对应的建议条目，不混进正文。

## 一、后台命令与终端会话（第三篇 8.1）

| 能力 | EvoFlow 真实位置 | 本项目位置 | 状态 | 差异 |
|---|---|---|---|---|
| 危险命令判定 | `tools/host_direct/terminal_tool.py:553` `_check_dangerous(command) -> str \| None` | `tools/host_direct/terminal_tool.py` 同名 | 已实现 | 原版返回**警告文本**并要求 `force:` 前缀确认，**没有** ALLOW/ASK/DENY 三态枚举 |
| 危险模式表 | `terminal_tool.py:506` `_DANGEROUS_PATTERNS` | 同名 | 已实现 | 正则列表 + 危险类别 id |
| 前台执行 | `terminal_tool.py:173` `_run_subprocess` | 同名 | 已实现 | |
| PTY 执行 | `terminal_tool.py:61` `_run_via_pty` | 不做 | 不实现 | 学习版只做 subprocess，理由见建议 1 |
| 后台执行 | `terminal_tool.py:438` `_spawn_background` | 同名 | 已实现 | |
| 自动转后台 | `terminal_tool.py:518` `_should_auto_background` | 同名 | 已实现 | |
| 前台超时 | `terminal_tool.py:524` `_foreground_timeout` | 同名 | 已实现 | |
| 超时后提示 | `terminal_tool.py:534` `_timeout_recovery_hint` | 同名 | 已实现 | |
| 工具入口 | `terminal_tool.py:567` `terminal_tool(...)` | 同名 | 已实现 | |
| 会话状态 | `tools/host_direct/terminal_session.py:109` `class ThreadShellState` | 同名 | 已实现 | 原版是线程级 shell 状态（cwd / 环境 / 历史命令） |
| 命令拼接 | `terminal_session.py:87` `_flatten_command` | 同名 | 已实现 | |
| 标记输出解析 | `terminal_session.py:134` `_parse_marked_output` | 同名 | 已实现 | 用 marker 分隔 stdout / exit code |
| 结果整形 | `terminal_tool.py:129` `_format_subprocess_output`、`:425` `_format_result` | 同名 | 已实现 | |

## 二、浏览器桥与 Computer Use（第三篇 8.2）

EvoFlow 的浏览器与 CUA **不是 Agent 工具，而是 HTTP 桥**（挂在 gateway，供浏览器扩展 / 桌面端调用）：

| 能力 | EvoFlow 真实位置 | 本项目位置 | 状态 | 差异 |
|---|---|---|---|---|
| 浏览器执行 | `app/gateway/routers/browser_bridge.py:89` `execute_command(payload)` | 无 | 不实现 | 原版是 REST 路由，带 `_bridge_token_guard` |
| 标签页列表 | `browser_bridge.py:133` `list_tabs` | 无 | 不实现 | |
| 传输状态 | `browser_bridge.py:104` `get_transport` | 无 | 不实现 | |
| 日志上报 | `browser_bridge.py:63` `append_browser_log` | 无 | 不实现 | |
| 浏览器快照 | `app/gateway/routers/browser_snapshots.py` | 无 | 不实现 | |
| CUA 执行 | `app/gateway/routers/cua_bridge.py:111` `execute(payload)` | 无 | 不实现 | 原版走 PowerShell（`_run_ps_action`，:77） |
| CUA 结果转换 | `cua_bridge.py:157` `_to_call_tool_result` | 无 | 不实现 | |

结论：本项目没有网关层，8.2 不实现代码；文档改为「说明原版形态 + 说明本项目为何不做」，不再给假签名。

## 三、上下文预算与自动续跑（第三篇 9.2）

| 能力 | EvoFlow 真实位置 | 本项目位置 | 状态 | 差异 |
|---|---|---|---|---|
| 上下文折叠 | `agents/middlewares/context_compaction_middleware.py`（`compaction_folded_this_call`、`compaction_fold_msg_counts` 等） | `middleware/context_compaction.py` | 已实现 | 原版是**折叠旧消息**（fold），不是按 token 硬裁断 |
| 续跑中间件 | `agents/goal/goal_auto_continue_middleware.py:120` `class GoalAutoContinueMiddleware` | `middleware/goal_auto_continue.py` 同名类 | 已实现 | 原版用 `after_model` + `hook_config(can_jump_to=["model","end"])` 跳转回模型节点，**不是** while 循环 |
| 同步钩子 | `goal_auto_continue_middleware.py:125` `after_model` | 同名 | 已实现 | |
| 异步钩子 | `goal_auto_continue_middleware.py` `aafter_model` | 同名 | 已实现 | |

注意：原版没有名为 `ContextBudgetMiddleware` 的类；`MAX_CONSECUTIVE_FAILURES` 在 EvoFlow 里是 `app/channels/weixin.py:52` 的微信推送重试常量（=3），与续跑无关——此前文档把它当成续跑上限是错的。

## 四、流式事件与 SSE（第三篇 10.2）

| 能力 | EvoFlow 真实位置 | 本项目位置 | 状态 | 差异 |
|---|---|---|---|---|
| 事件编码 | `app/gateway/agui_stream_encode.py:10` `encode_agui_event(event) -> bytes` | `events/sse.py` `encode_sse_event` | 已实现 | 原版编码成 AG-UI 协议字节流 |
| 事件解码 | `agui_stream_encode.py:19` `decode_agui_payload` | 同名 | 已实现 | |
| 事件生成器 | `app/gateway/routers/events.py:133` `event_generator(thread_id)` | `app_server/sse.py` | 已实现 | 原版用 `asyncio.Queue` + `_enqueue_sse` 推送 |
| 订阅端点 | `events.py:178` `subscribe_task_events(request, task_id)` | `app_server/sse.py` | 已实现 | |
| 心跳 | `events.py:221` `emit_task_heartbeat` | 同名 | 已实现 | 防中间代理断连 |

## 五、建议

以下每条都可以单独扩成一节，正文不展开：

1. **命令风控不要做三态枚举**：原版 `_check_dangerous` 返回警告文本 + `force:` 前缀，好处是模型能看懂“为什么被拦、怎么确认”，三态枚举反而要求模型理解一个它看不见的枚举值。建议照原版。
2. **PTY 不实现**：`_run_via_pty` 解决的是交互式程序（vim、top）的输出问题，学习版只跑一次性命令，subprocess 够用；差异写清即可。
3. **浏览器桥不搬进 harness**：原版把它放 gateway，是因为浏览器扩展要跨进程回调。本项目没有网关，硬搬到工具层会造出一个假接口。建议明确“本项目不做浏览器”。
4. **上下文管理用折叠而非截断**：折叠保留语义（旧消息压成摘要），截断会丢因果关系。建议实现 `context_compaction` 的折叠思路，而不是 `MAX_TOKENS` 一刀切。
5. **自动续跑用跳转而非循环**：原版靠 LangGraph 的 `can_jump_to=["model","end"]` 回到模型节点，图状态天然持久化；自己写 while 循环会绕开 checkpoint，恢复后步数丢失。
6. **SSE 用编码函数而非散落 print**：`_execute_stream_and_print` 里的 print 应替换为 `encode_sse_event(event)` 的 `yield`，事件结构不动，这样终端与 HTTP 两个消费方共用一套事件。

## 六、撤销清单

| 已写入文档的错误符号 | 处理 |
|---|---|
| `CommandDecision`（ALLOW/ASK/DENY） | 删除，改为 `_check_dangerous` + `force:` 语义 |
| `check_command(command, cwd)` | 删除，原版无此函数 |
| `kill_process_group` | 删除，原版无此函数 |
| `CommandSession.start/read/stop` | 删除，原版为 `ThreadShellState` |
| `check_site` | 删除，原版无此函数（站点策略在 `browser_bridge` 的 guard 里） |
| `BrowserSession.open/snapshot/click/type_text/close` | 删除，原版无工具层会话类 |
| `DESTRUCTIVE_ACTIONS` | 删除，原版无此常量 |
| `ContextBudgetMiddleware` | 删除，原版为 `context_compaction_middleware` 模块 |
| `ShareRepository`（第二篇 4.3） | 标注「本项目新增设计，原版无此符号」 |

## 七、实测记录

本轮代码全部在 `backend/` 下用 `uv run --project packages/harness` 实际执行过：

| 验证项 | 命令要点 | 实际结果 |
|---|---|---|
| 终端工具注册 | `default_catalog().names()` | `['calculator','list_directory','read_text_file','terminal']` |
| 别名解析 | `c._alias_index` | `shell/bash/term → terminal` |
| 命令执行 | `terminal_tool.invoke({'command':'echo hello-wah'})` | 返回 `hello-wah` |
| 危险命令拦截 | `_check_dangerous('rm -rf /tmp/x')` | 返回非 None（被拦，未执行） |
| 自动转后台 | `_should_auto_background('npm install', False)` | `True` |
| 上下文折叠 | 8 条 3000 字符消息过 `before_model` | 返回 3 条（2 条删除 + 1 条摘要），计数 `(8, 7)` |
| 续跑不触发 | FakeChatModel 回复无未完成标记 | 消息数 2，续跑 0/8 |
| 续跑到上限 | `GenericFakeChatModel` 恒回"下一步要做 A" | 消息数 10 后停在 end，无递归超限 |
| SSE 编码 | `--sse --once "计算 6*7"` | 5 帧：run_start / tool_call / tool_result / text_delta / run_end |

踩到的真实坑（已修，写在这里避免重犯）：

1. **`jump_to` 的计数不能用 `ContextVar`**。LangGraph 每跳一个节点都新建执行上下文，`ContextVar` 的写入不跨节点保留，实测计数永远为 0 → 无限跳回 model → `GraphRecursionError: Recursion limit of 10000`。改成按 `thread_id` 的进程内 dict 后才正常。原版把步数存在 goal 行（数据库）里，本质是同一个"外部状态"思路。
2. **未完成判据不能含"继续""接着"**。用户输入含"继续"时模型会回显，判据命中后永远续跑。只保留 `TODO / 待办 / 尚未完成 / 下一步` 四个结构化味道更强的词。
