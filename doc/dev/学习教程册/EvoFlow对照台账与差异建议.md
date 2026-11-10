# EvoFlow 对照台账与差异建议

这份台账是**唯一事实源**：文档里出现的每个文件、类、方法，都必须能在「EvoFlow 真实位置」或「本项目位置」查到。查不到的不许写。

台账建立的直接原因：第三篇 10.1 / 10.2 / 11.2 三节此前写了 9 个不存在的符号（`CommandDecision`、`check_command`、`kill_process_group`、`CommandSession`、`check_site`、`BrowserSession`、`DESTRUCTIVE_ACTIONS`、`ContextBudgetMiddleware`、`ShareRepository`），原因是先写签名再去查原版。规则从这一篇起反向执行：**先查、再写**。

## 使用规则

1. 写代码前先在本台账登记一行：能力 → 原版位置 → 本项目位置 → 状态。
2. 命名跟原版；形态不一致（简化、合并、改写）必须在「差异」列写明。
3. 原版有、本项目不做，标「不实现」并给理由，不写假签名。
4. 与原版有分歧、或认为该改的地方，写进[第五节](#五建议)对应的建议条目，不混进正文。

## 一、后台命令与终端会话（第三篇 10.1）

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

## 二、浏览器桥与 Computer Use（第三篇 10.2）

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

结论：本项目没有网关层，10.2 不实现代码；文档改为「说明原版形态 + 说明本项目为何不做」，不再给假签名。

## 三、上下文预算与自动续跑（第三篇 11.2）

| 能力 | EvoFlow 真实位置 | 本项目位置 | 状态 | 差异 |
|---|---|---|---|---|
| 上下文折叠 | `agents/middlewares/context_compaction_middleware.py`（`compaction_folded_this_call`、`compaction_fold_msg_counts` 等） | `middleware/context_compaction.py` | 已实现 | 原版是**折叠旧消息**（fold），不是按 token 硬裁断 |
| 续跑中间件 | `agents/goal/goal_auto_continue_middleware.py:120` `class GoalAutoContinueMiddleware` | `middleware/goal_auto_continue.py` 同名类 | 已实现 | 原版用 `after_model` + `hook_config(can_jump_to=["model","end"])` 跳转回模型节点，**不是** while 循环 |
| 同步钩子 | `goal_auto_continue_middleware.py:125` `after_model` | 同名 | 已实现 | |
| 异步钩子 | `goal_auto_continue_middleware.py` `aafter_model` | 同名 | 已实现 | |

注意：原版没有名为 `ContextBudgetMiddleware` 的类；`MAX_CONSECUTIVE_FAILURES` 在 EvoFlow 里是 `app/channels/weixin.py:52` 的微信推送重试常量（=3），与续跑无关——此前文档把它当成续跑上限是错的。

## 四、流式事件与 SSE（第三篇 12.2）

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
| `ShareRepository`（第二篇 5.3） | 标注「本项目新增设计，原版无此符号」 |
| 「原版没有渠道适配器/消息总线」（第 46 章旧版全文前提） | **整条撤销**。原版真实存在：`backend/app/channels/base.py:50 class Channel(ABC)`、`message_bus.py:130 class MessageBus`、`manager.py:1870 class ChannelManager`，六个渠实现齐全。第 46 章已整章重写为仿写章 |

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

## 八、本项目自造符号（原版无对应）

这些符号在 EvoFlow 里**查不到**，是本项目为教学闭环新造的。文档里出现时必须带来源声明，不许写成"对齐原版"。

| 符号 | 本项目位置 | EvoFlow 对应情况 | 处理 |
|---|---|---|---|
| `calculator` | `tools/builtins/calculator.py:69` | **无同名工具**（算术走 `builtins/code_execution_tool.py` 与 `builtins/process_tool.py`） | 文档标注"本项目自造" |
| `safe_eval` | `tools/builtins/calculator.py:60` | 无 | 同上 |
| `_eval_node` | `tools/builtins/calculator.py:41` | 无 | 同上 |
| `build_calculator_tool` | `tools/builtins/calculator.py:83` | 无 | 同上；实现与 docstring 不符（详见第七节） |
| `ToolResult` / `shape_result` | `tools/result.py:20`、`:53` | 功能对应 `tools/tool_result_shaper.py`，**符号名不同** | 标注"功能对齐、命名自造" |
| `ShareRepository` | **未落地**（5.3 只是目标设计，仓库中无 `persistence/share_repository.py`） | 原版有 `persistence/chat_share_repositories.py` + `app/gateway/routers/share.py` | 标注"仅设计、未实现"，`WAH-RUN-010` 待盘点 |
| `workspace_file.py`（`workspace_root` / `resolve_in_workspace` / `read_text_file` / `list_directory`） | `tools/builtins/workspace_file.py` | 无此文件；原版拆成 `host_direct/read_file.py`、`list_dir.py`、`write_file.py`、`workspace_path_guard.py` | 标注"本项目合并实现，仅只读" |
| `_resolve_cwd` | `tools/host_direct/terminal_tool.py:164` | 无此私有函数；原版调 `workspace_path_guard.resolve_tool_workdir(workdir, runtime=…)`（`terminal_tool.py:32` 导入、`:627` 调用） | 已在 docstring 标注，属"命名自造、功能对应" |

核实方法（可复现）：

```bash
grep -rln "calculator|safe_eval|ast.parse" /Users/main/EvoFlow/backend/packages/harness/evoflow/tools/
# → 零匹配
```

## 九、同名不同义与改名对照（不能写成"原版没有"）

第八节是"原版查不到"。本节相反：**原版有，但类名/签名/职责被改过**。这类符号最容易在文档里被误写成"自造"或"对齐原版"，必须逐条写清关系。

**命名沿革先说清楚**：`ModelConfig`（EvoFlow，Pydantic）→ `ChatModelConfig`（AgentFlow 第一遍，`config/model_config.py:44`，`@dataclass`）→ 本项目沿用 `ChatModelConfig`，只是加了 `frozen=True` 与显式类型校验。所以 `ChatModelConfig` **不是本项目发明**，它来自第一遍仿写。

| 本项目符号 | EvoFlow 真实符号 | 关系 | 差异要点 |
|---|---|---|---|
| `config/model_config.py::ChatModelConfig`（frozen dataclass，5 字段） | `config/model_config.py:86::ModelConfig`（Pydantic `BaseModel`，20+ 字段） | **改名（命名源：AgentFlow 第一遍）+ 换技术栈** | 原版有 `use`（provider 类路径）、`name`/`model` 双名、`request_timeout`/`max_retries`/`max_tokens`/`context_length`；本项目全无 |
| `models/factory.py::create_chat_model(config, *, runtime_model, runtime_provider)` | `models/factory.py:845::create_chat_model(name, thinking_enabled, *, thinking_type, invocation_kind, **kwargs)` | **同名不同签名**（本签名沿用 AgentFlow `create_chat_model(cfg)`） | 原版按模型名查配置行、只实例化 `use` 类路径；本项目直接吃配置对象、内部 `if/elif` 分支 |
| `models/credential_loader.py::resolve_api_key` / `mask_api_key` / `sanitize_error` | ① `models/credential_loader.py`（Claude Code / Codex CLI 文件凭证、OAuth）② `models/credential_sanitize.py::sanitize_api_key` / `is_masked_api_key` / `resolve_credential_reference` | **同名不同职责 + 功能分散对应** | 原版 credential_loader 管的是 CLI 凭证文件，不管 API key 解析；脱敏逻辑在 credential_sanitize |
| `models/resolver.py::resolve_provider` / `resolve_model_name` | `models/resolver.py::resolve_run_model` / `resolve_run_model_with_source` | **拆分** | 原版一函数带 `agent_code` / `cfg` / `require_configured`，三级阶梯；本项目拆两个，缺 agent 级 |
| `config/loader.py::load_chat_model_config` | `config/models_yaml.py` + `config/app_config.py` 的加载路径 | **收窄重写** | 原版加载 `models.providers` 段并并入 `AppConfig`；本项目只加载 `models.chat` |

配套核实命令：

```bash
grep -n "^class " /Users/main/EvoFlow/backend/packages/harness/evoflow/config/model_config.py
# → 86:class ModelConfig(BaseModel)

grep -n "def create_chat_model" /Users/main/EvoFlow/backend/packages/harness/evoflow/models/factory.py
# → 845:def create_chat_model(

grep -rn "resolve_effective_config\|FakeChatModel\|mask_api_key\|sanitize_error" \
  /Users/main/EvoFlow/backend/packages/harness/evoflow/
# → 零匹配（这四个确属本项目自造）
```

**判据**：原版查不到 → 第八节"自造"；原版有但名/义不同 → 本节"改名/同名不同义"。两者不能混用。

### 目录级同名不同义（第四篇以后重写时核实，2026-11）

这三条是**按目录名去找功能会走错路**的典型，写文档时最容易误标"原版没有"或"原版就是这样"。

| 目录名 | 直觉以为 | 实际是什么 | 核实符号 |
|---|---|---|---|
| `scheduler/` | 定时任务调度器（cron） | **一次任务内的工具编排**：预取、编辑后 lint、读重试、子代理流桥接。与 cron 无关 | `engine.py:52 class LocalToolScheduler`、`task_plan.py:16 TaskOp` / `:27 TaskPlan` / `:32 parse_task_plan_from_text`、`tool_executor.py:24 execute_op`、`rules.py:33 classify_ops`、`retry.py:11 retry_read`、`post_edit_lint.py:128 follow_lint_after_edit` |
| 真正的"定时"在 `proactive/schedule.py` | — | **RRULE/旧格式 → cron 的迁移链 + 关闭判定** | `is_schedule_off:35`、`_parse_rrule_parts:40`、`looks_like_legacy_rrule:49`、`legacy_rrule_to_cron:56`、`migrate_stored_schedule:118` |
| `plans/` | 任务计划 / Plan 定义 | **套餐能力授权**（tier entitlement、vendor plan 校验） | `tier_entitlements:164`、`assert_vendor_plan_allows:100` |

**任务计划实际在 `collab/`**：`plan_session_task.py`、`plan_subtasks_sync.py`、`supervisor_plan_gate.py`。状态机在 `can_transition:108` / `validate_transition:122` / `get_allowed_transitions:136` + `InvalidStateTransitionError:102`；子任务另有一套 `subtask_state_machine.py`（`normalize_subtask_status:44`、`is_terminal:51`、`is_active:55`、`can_advance:59`）。

### ~~归入第八节（原版确实没有，属设计稿而非仿写）~~ —— 已撤销，见下

| 本项目/文档里的概念 | 核实结论 | 依据 |
|---|---|---|
| ~~渠道适配器（`ChannelAdapter`）、消息总线（`MessageBus`）、渠道健康表、入站 webhook 处理~~ | **原判断错误，已撤销。原版真实存在**（2026-11 按 `1e393d9dfba9` 复核） | `backend/app/channels/` 在旧基准 `87a9577` 时即已存在；`base.py:50 class Channel(ABC)`、`message_bus.py:130 class MessageBus`、`manager.py:1870 class ChannelManager`；`Channel` 子类：`feishu.py`/`wecom.py`/`weixin.py`/`dingtalk.py`/`slack.py`/`telegram.py` |
| ~~第 46 章全部设计「不可标为仿写」~~ | **同样撤销**。第 46 章已整章重写为仿写章 | 同上 |

**这次错误怎么产生的**：只搜了 `evoflow/` 核心包，没有搜 `backend/app/channels/`，然后据"核心包无命中"断言"原版没有"。`ChannelAdapter` 这个名字原版确实没有（原版叫 `Channel`），但**名字不同不等于功能不存在**——只按一个名字去否定，是二次翻车。

**修正后的判据**：一个能力是否存在于原版，要看**行为**，不是看某个具体类名。先按功能找目录（渠道 → `backend/app/channels/`、Gateway → `backend/app/gateway/`），再在目录内找同类职责的类，最后才判"有/无"。

### 本轮（`1e393d9dfba9`）新增的真实能力

| 新增域 | 位置 | 是否接线 | 影响 |
|---|---|---|---|
| 人格内核 | `person_kernel.py`（2028 行/49 函数）、`person_affect.py`（351/17）、`person_wrap_up_reflect.py`（720/11）；三者是核心包**顶层文件**，不在任何包目录 | 是：`agents/lead_agent/prompt.py:1964–2025`（soul/affect/memory/craft 注入）、`config/agents_config.py:1732/1847`（`ensure_agent_identity`）、`admin/tasks.py:1513`（`on_handoff_dispatched`）、`admin/employee_front_desk.py:391`（脱敏简报）、`tools/builtins/person_memory_edit_tool.py:140`（自编辑）、`persistence/person_relations_repositories.py`（两张表） | **已入课**：`WAH-PERSON-001–012`，第 53 章 |
| 入站渠道细分 | `channels/feishu_inbound_parse.py`、`feishu_inbound_media.py`、`feishu_inbound_coalesce.py`、`feishu_inbound_trace_log.py`、`inbound_media_store.py`、`outbound_text.py` | 是 | 第 46 章已纳入 |
| Gateway 新路由 | `routers/audit.py`、`codex_auth.py`、`openai_compat_models.py` | 是 | 第 35/36 章需复核 |

**核实方法（强制）**：先 `ls -1 <dir>/` 看文件清单 → 再逐文件 `grep -n "^class \|^def "` → 再读文件头 docstring → 再按**功能**搜全仓库（含 `backend/app/`）→ 最后才下结论。

**判据**：原版查不到（按功能搜全仓库）→ 第八节"自造"；原版有但名/义不同 → 本节"改名/同名不同义"。**名字不同不能作为"不存在"的证据。**
