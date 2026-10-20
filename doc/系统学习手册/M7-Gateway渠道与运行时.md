# M7 — Gateway、Channels 与服务运行时

> 本章的实现目标是 WorkAgentHarness。文中出现的 AgentFlow 路径、状态和第一次学习记录均为历史对照；WorkAgentHarness 当前状态以本仓库和 02 全量功能矩阵为准。

## 本章目标

理解核心库如何装入可运行服务：HTTP 路由、鉴权依赖、SSE/长连接、IM 入站出站、消息总线、runtime ports/adapters、后台工作和生命周期。按 API/渠道/管理面等类别完整盘点，而不只对照一条 Feishu 路径。

## 阅读入口

> **路径约定**：EvoFlow 核心表项中的 `evoflow/...` 相对 `backend/packages/harness/`；AgentFlow 第一版中的 `agentflow/...` 相对同仓库的 `backend/packages/harness/`。以 `backend/...` 或 `evopanel/...` 开头的路径相对各仓库根目录。

| 功能 | EvoFlow | AgentFlow 第一版参考（WorkAgentHarness 映射见 02） |
|---|---|---|
| 应用层 App/Gateway | EvoFlow `backend/app/` | AgentFlow `backend/app/` |
| 核心层应用服务器 | EvoFlow `backend/packages/harness/evoflow/app_server/` | 初学版无等价独立服务域；从 Gateway 与核心装配追差异 |
| Gateway | `backend/app/gateway/app.py`、`backend/app/gateway/routers/`、`backend/app/gateway/events/`、`backend/app/gateway/streaming/` | `backend/app/gateway/app.py`、`backend/app/gateway/routers/{auth,models,runs,threads}.py`、`backend/app/gateway/sse.py` |
| Runtime ports | `backend/packages/harness/evoflow/runtime/ports.py`、`backend/app/gateway/runtime_adapters.py` | `backend/packages/harness/agentflow/runtime/ports.py`、`backend/app/gateway/runtime_adapters.py` |
| Channels | `backend/app/channels/` | `backend/app/channels/{base,message_bus,manager,feishu}.py` |
| 应用层协议/服务 | EvoFlow `backend/app/gateway/v4/`、`backend/app/gateway/speech/`、`backend/app/gateway/cancellation/` | 初学版没有完整覆盖，分配到 M7/M8 差异项 |
| 核心层协议/取消 | EvoFlow `backend/packages/harness/evoflow/a2a/`、`backend/packages/harness/evoflow/cancellation/` | 初学版没有完整覆盖，分配到 M4/M6/M7 差异项 |

## 四级学习

### 核心代码讲解清单

逐段讲解 `app/gateway/app.py` 的 factory/lifespan/router wiring、一个真实 router/service/dependency、SSE/event emitter、`app/channels/base.py`、`message_bus.py`、`manager.py` 和一个 channel；再追 `evoflow/runtime/ports.py` 的接口及 app adapter 注册。每处说明谁调用、请求/事件结构、认证条件、进程内状态、错误路径和关闭清理。

### L1 入门闭环

FastAPI health route → fake runner → 一次请求和响应；接着通过一条 fake inbound message 将输入交给 Agent 并返回文本。

### L2 基础能力

补路由装配/lifespan、配置、依赖注入、认证/授权、API schema、错误格式、SSE 解析、run/thread 管理。Channel 通过 base interface、MessageBus、Manager 接线，验证去重、发送失败和 shutdown。

### L3 完整功能

逐类盘点所有 router 与公开 API（模型、run/thread/session、知识、文件、协作/任务、插件、组织、browser、speech、A2A、automation、eval、health/admin 等，以固定快照实际清单为准）；所有渠道及消息类型（文字、文件、卡片、流式更新、快捷命令、会话索引）；SSE/events/streaming 恢复或镜像；服务启动、依赖注册、ports/adapters、后台任务、进程健康和资源关闭。确认每个路由/渠道真正挂载并经过授权。

### L4 高级边界

覆盖多 worker/多进程状态一致性、event replay、流断开与取消、反压、消息重复与乱序、渠道限流、Webhook 校验、启动失败部分清理、健康探针差异、优雅关闭、运行时 adapter 缺失和端口注册竞争。区分 memory-only 与 durable service。

## 必须逐一回答

- 是谁创建 app？lifespan 的先后顺序和后台任务有哪些？
- 路由注册在哪里？哪些是默认路径、哪些是扩展/延迟挂载？
- token 在哪校验、权限按什么资源判断？签发成功是否意味着受保护？
- SSE 是否直连 Agent 的增量事件，还是先 invoke 后把完整文本包装成 delta？
- bus/manager 是真的负责渠道收发，还是 Feishu 仍内联处理？
- runtime port 如何避免 core import app？每个 port 有没有生产 adapter？

## 练习与验收

AgentFlow 第一版的 Archify 图（历史参考）：[M7 Gateway 与渠道图](/Users/main/AgentFlow/doc/doc-dev/01-里程碑/diagrams/M7-gateway-api-im-20261011-034339/M7.html)。该图展示初版单渠道路径；MessageBus/ChannelManager 尚未接入 Feishu 主链路，不能把图中的目标结构当作当前实现。

1. **Feishu 入站到回发端到端验收（§7 P2 关闭出口）**：先按目标职责接通 `Feishu event → 规范化 InboundMessage → MessageBus 入站队列 → dispatcher/ChannelManager → Agent → OutboundMessage → MessageBus 出站订阅 → Feishu sender`。使用 fake Feishu transport、fake Agent 和可记录调用顺序的 sender，提交一条入站消息，并断言每个节点只经过一次、回复内容和 chat/thread 路由正确。测试必须通过与服务实际启动相同的装配入口；分别对 bus publish/get、manager 路由、Agent runner、出站注册回调做 spy/assert，证明 Agent 和 sender 没有被 Feishu 内联路径绕过。当前 `FeishuChannel.on_message` 仍直接调用 Agent 和 sender，现有 `test_channel_bus_manager.py` 只验证 bus/manager 单体契约，因此在生产装配改造和该集成验收通过前，此关闭出口保持未完成。
2. 对重复消息、Agent 异常、sender 失败、未注册 channel 和 shutdown 做集成测试；记录哪些状态会重试、丢弃或保留，确认不会重复回发。
3. 给每个 runtime port 列出调用者、生产 adapter 和契约测试；从一个真实 Gateway/API 请求走过 port 到 adapter，再验证 adapter 缺失和依赖失败时的行为。
4. 列出声明为 Web/API/IM 端到端支持的用户旅程，逐条验证入口、授权、核心服务、持久化和可见回显；没有端到端证据的能力保留为未完成。

## 深入链接

- 第一次学习记录：[M7 应用层](/Users/main/AgentFlow/doc/doc-dev/01-里程碑/M7-应用层.md)
- 代码说明：[Gateway app](/Users/main/AgentFlow/doc/doc-code/app/gateway/app.md)、[SSE](/Users/main/AgentFlow/doc/doc-code/app/gateway/sse.md)、[runtime ports](/Users/main/AgentFlow/doc/doc-code/runtime/ports.md)、[MessageBus](/Users/main/AgentFlow/doc/doc-code/app/channels/message_bus.md)、[ChannelManager](/Users/main/AgentFlow/doc/doc-code/app/channels/manager.md)
