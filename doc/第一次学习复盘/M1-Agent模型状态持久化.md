# M1 — Agent、模型、状态与持久化

> 本章的实现目标是 WorkAgentHarness。文中出现的 AgentFlow 路径、状态和第一次学习记录均为历史对照；WorkAgentHarness 当前状态以本仓库和 02 全量功能矩阵为准。

## 本章目标

从配置和一个用户输入开始，理解模型解析、Lead Agent 组装、LangGraph state、会话数据和 checkpoint 的不同责任；最后覆盖固定 EvoFlow 快照中属于运行核心的 Agent 生命周期和模型能力。

## 阅读入口

> **路径约定**：EvoFlow 核心表项中的 `evoflow/...` 相对 `backend/packages/harness/`；AgentFlow 第一版中的 `agentflow/...` 相对同仓库的 `backend/packages/harness/`。以 `backend/...` 或 `evopanel/...` 开头的路径相对各仓库根目录。

| 职责 | EvoFlow | AgentFlow 第一版参考（WorkAgentHarness 映射见 02） |
|---|---|---|
| 配置与路径 | `backend/packages/harness/evoflow/config/` | `backend/packages/harness/agentflow/config/` |
| 模型工厂/解析 | `.../evoflow/models/` | `.../agentflow/models/` |
| 主 Agent 与状态 | `.../evoflow/agents/lead_agent/`、`agents/thread_state.py` | `.../agentflow/agents/lead_agent/`、`agents/thread_state.py` |
| Checkpoint | `.../evoflow/agents/checkpointer/` | `.../agentflow/agents/checkpointer/` |
| 业务持久化 | `.../evoflow/persistence/` | `.../agentflow/persistence/` |
| CLI 装配 | `.../evoflow/cli/` | `.../agentflow/cli/` |

`...` 表示相同的 `backend/packages/harness/` 前缀。先阅读工厂、类型、调用者和测试，再下钻大文件，不以文件名相同判断行为相同。

## 四级学习

### L1 入门闭环

fake chat model → 配置读取 → 构造 Lead Agent → 输入一条 HumanMessage → 得到 AIMessage。只保留最少 state 和内存 checkpoint；画清调用顺序。

### L2 基础运行能力

加入真实配置解析、model factory/resolver、主模型选择、参数校验和可安全读取的 secret 配置；区分业务会话/消息表与 LangGraph checkpoint。验证相同 thread 连续运行、关闭进程后恢复、创建/清理 thread。

### L3 完整功能

根据 EvoFlow `config/`、`models/`、Lead Agent、checkpointer 和 persistence 的实际调用点，逐项核对：provider/协议兼容、模型选择/fallback、模型能力元数据、重试/超时、结构化输出、Agent 状态字段、消息格式、thread 生命周期、checkpointer backend、历史读写、数据清理、数据库初始化/迁移。每个功能映射到 AgentFlow 或登记缺失；一个 fake 模型不代表 provider 对齐。

### L4 高级边界

覆盖模型不可达、超时、限速、无效配置、部分 checkpoint、并发 thread、重复请求、持久化失败、恢复/删除、schema 迁移与密钥泄漏风险。核对 async 入口是否误用同步驱动。

## 核心概念讲解清单

本章逐段讲解的代码位置：EvoFlow/AgentFlow 第一版的 `config/app_config.py`、`config/models_yaml.py`、`models/factory.py` 与 `models/resolver.py`（以固定快照实际存在者为准）；`agents/thread_state.py`、`agents/lead_agent/agent.py`、`agents/checkpointer/`；`persistence/db.py`、`bootstrap.py`、session repositories。对每处说明调用方、配置/消息输入、对象或数据库输出、错误传播和恢复行为，并引用对应测试。

AgentFlow 第一版的 Archify 图（历史参考）：[M1 Agent 闭环图](/Users/main/AgentFlow/doc/doc-dev/01-里程碑/diagrams/M1-minimal-agent-20261011-034339/M1.html)。它用于理解初版最小路径；需随 provider/checkpointer 全量盘点更新。

- **配置**是可变的运行输入；**模型工厂**将配置转换成可调用模型对象。
- **Agent graph**定义处理节点和工具循环；**ThreadState**是 graph 在一次会话中的业务状态。
- **会话表**服务产品会话索引/消息记录；**checkpoint**保存图执行恢复状态，两者不能互相冒充。
- **invoke**等待最终结果；**stream**逐事件产出。具体是否逐 token 取决于模型与 runner，不能由 SSE endpoint 名称推断。

## 动手练习与验收

1. 假模型执行两轮，断言 thread state 和消息累积正确。
2. 用 SQLite checkpoint 重启恢复；同时查看业务表和 checkpoint 数据分别写了什么。
3. 对每种配置/provider 变体做表驱动测试，至少包含缺字段、无效参数和供应商错误。
4. 从 CLI 与真实应用装配入口各跑一遍；分别证明 provider、线程恢复和错误路径。

完成证据：代码路径映射、数据库/状态图、模型 provider 清单、测试命令与实测结果、未覆盖 provider 的原因。

## 深入链接

- 第一次学习记录：[M1-最小 Agent](/Users/main/AgentFlow/doc/doc-dev/01-里程碑/M1-最小Agent.md)、[M1 思考与规划](/Users/main/AgentFlow/doc/doc-dev/01-里程碑/M1-思考与规划.md)
- 代码说明：[config](/Users/main/AgentFlow/doc/doc-code/config/设计说明.md)、[models](/Users/main/AgentFlow/doc/doc-code/models/设计说明.md)、[agents](/Users/main/AgentFlow/doc/doc-code/agents/设计说明.md)、[persistence](/Users/main/AgentFlow/doc/doc-code/persistence/设计说明.md)
