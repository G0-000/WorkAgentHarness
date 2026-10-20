# M6 — MCP、插件、治理与可观测性

> 本章的实现目标是 WorkAgentHarness。文中出现的 AgentFlow 路径、状态和第一次学习记录均为历史对照；WorkAgentHarness 当前状态以本仓库和 02 全量功能矩阵为准。

## 本章目标

从外部能力接入扩展到系统治理：理解连接池和 MCP server 生命周期、provider/plugin 安装与运行、主体身份/授权、组织隔离、审计和 trace。逐项区分组件实现与真实入口集成。

## 阅读入口

> **路径约定**：EvoFlow 核心表项中的 `evoflow/...` 相对 `backend/packages/harness/`；AgentFlow 第一版中的 `agentflow/...` 相对同仓库的 `backend/packages/harness/`。以 `backend/...` 或 `evopanel/...` 开头的路径相对各仓库根目录。

| 领域 | EvoFlow | AgentFlow 第一版当前映射 |
|---|---|---|
| MCP | `evoflow/mcp/` | `agentflow/mcp/` |
| 社区 provider | `evoflow/community/` | `agentflow/community/`（当前仅部分 provider） |
| Plugins/skills | `evoflow/plugins/`、`skills/`、`capability/` | `agentflow/skills/`；plugin system 需补全 |
| Auth/governance | `authz/`、`webui/`、`organizations/`、`license/`、`guardrails/` | `agentflow/authz/`、`webui/`（部分） |
| Observability | `observability/`、trace/query/storage | `agentflow/observability/`（部分） |
| 外部 Agent | `external_agents/`、A2A 配套 | 需列入功能差异表 |

## 四级学习

### 核心代码讲解清单

按 client/connection manager → MCP tool adapter → Agent tool registration 解释协议接入；按 provider/plugin registry → config/credential → lifecycle hook 解释扩展管理；按 principal/authz guard → protected route/tool 解释授权；按 recorder → trace store/query 解释观测。说明组件是否被正常入口装配，以及失效/撤权/断连时的行为。

### L1 入门闭环

起本地 fake MCP server，完成 initialize→list tools→把一个工具注册进 Agent→调用→关闭连接。全程不接真实第三方凭据。

### L2 基础能力

补配置校验、传输选择、连接池、超时/重连、错误隔离、工具命名空间；对一个受保护 HTTP route 做 token 校验；记录一条 trace 并可查询。

### L3 完整功能

核对 MCP 多传输与连接生命周期、server/tool/resource/prompt 能力、社区 provider 注册/启停/凭据、plugin manifest/发现/安装/启用/禁用/升级、skills/capability、用户与组织主体、权限 preset/ACL/资源可见性、Web UI auth middleware、token 生命周期、审计、trace spans/事件/store/query、guardrails/license 和 fallback。检查所有工具/路由/前端真实装配，独立组件测试不算接线完成。

### L4 高级边界

验证恶意/失效 MCP server、协议错误、连接泄漏、重连风暴、provider rate limit、凭据隔离、跨组织访问、撤销 token、权限变化中任务、审计不可抵赖、trace 敏感数据脱敏、plugin 版本冲突和降级。

## 练习与验收

AgentFlow 第一版的 Archify 图（历史参考）：[M6 扩展与治理图](/Users/main/AgentFlow/doc/doc-dev/01-里程碑/diagrams/M6-extensions-governance-20261011-034339/M6.html)。图只覆盖初版组件；plugin、organization 和治理入口盘点后需更新。

1. 用可控 MCP server 产生正常/超时/协议错误，确认 Agent 和 UI 的失败表现。
2. 让未授权主体访问一个受保护 endpoint、工具和另一组织资源，三处都应拒绝并留下安全事件。
3. 验证插件安装/停用后工具目录变化，运行中的 session 如何处理旧 binding。
4. 将一次真实用户请求从 trace 起点追到模型、工具、数据库和外部 provider，并验证 query/filter/redaction。
5. 从 [02-全量功能矩阵](02-全量功能矩阵.md) 筛出 plugins/organizations/A2A/authz 等本章功能 ID，为每项指出真实注册入口和调用者；至少选一条用户或 Agent 请求穿过授权/组织边界、扩展装配与审计/trace，并用集成或端到端证据验收。未接入的组件保留为未完成，供 §5.3 汇总。

## 深入链接

- 首次学习记录：[M6 扩展与治理](/Users/main/AgentFlow/doc/doc-dev/01-里程碑/M6-扩展与治理.md)
- 代码说明：[MCP client](/Users/main/AgentFlow/doc/doc-code/mcp/client.md)、[MCP tools](/Users/main/AgentFlow/doc/doc-code/mcp/tools.md)、[authz guard](/Users/main/AgentFlow/doc/doc-code/authz/http_guard.md)、[observability](/Users/main/AgentFlow/doc/doc-code/observability/recorder.md)
