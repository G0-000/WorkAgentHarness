# EvoFlow 分层源码阅读

基准 commit 62a4117ceff4626213ad434eae6b311bcc3bcfe1。此页仅导航；逐项补真实 caller、符号和测试。

入口：CLI 位于 backend/packages/harness/evoflow/cli/；HTTP、SSE、v4、speech 在 backend/app/gateway/；IM 位于 backend/app/channels/；app server 在 evoflow/app_server/；Web/桌面位于 evopanel/src/，包括 zcode-ui、zcode-services、zcode-shared、zcode-rpc 和 zcode-provider。

核心包 backend/packages/harness/evoflow/ 中，对话从 config/models/agents/persistence 入手；工具看 tools/ 和 agents/middlewares/；上下文看 context/memory/knowledge/code_index/uploads/assets；执行与协作看 subagents/sandbox/execution_security/session_execution/plans/collab/workflows/automation/proactive；扩展治理看 mcp/plugins/skills/community/a2a/authz/organizations/observability/eval/admin。

backend/ARCHITECTURE.md 约定 app 可依赖 core，core 不反向依赖 app.*；通过 evoflow/runtime/ 的 port 和 app adapter 连接。追踪启动注册，不能只画理想架构。v4/speech 属 app 层；cancellation 在多处出现，要按调用链定职责。ZCode 和 evopanel 是产品学习范围的一部分。

下一步选真实用户旅程，记录入口注册、核心调用、状态变化、结果和测试，并写进对应功能 ID。
