# 第 3 章｜Agent 构建、角色与单轮执行

> 所属篇：启动一个可配置、可恢复的 Agent
> 功能范围：`WAH-RUN-003–004`
> 导航：[教程册总目录](../README.md) · [本篇导读](README.md) · [课程索引](../../学习手册/课程目录.md) · [功能路线](../../学习手册/功能单元路线.md) · [唯一状态清单](../../学习手册/功能清单.md)

## 本章要做出的东西
把模型变成真实用户请求能触发的 Agent：接收消息、构造角色与提示、执行模型、返回结果。此时不加入工具和复杂多 Agent 状态。

## EvoFlow 阅读顺序
1. 从 `backend/app/gateway/routers/chat_sessions.py` 找请求函数、schema、身份依赖和调用服务，记 session/thread 的创建时机。
2. 读 `agents/lead_agent/agent.py`：分开标注 Agent 构建与执行，圈出 model、system prompt、tools、middleware、checkpointer 的注入点。
3. 沿 `agents/lead_agent/prompt*.py` 看固定系统指令、角色配置、动态上下文如何合成。
4. 对照 `agents/goal/`、`agents/mission_state/`，说明它们与 lead agent 区别；本章只仿写单轮调用。
5. 从 route/service 跟到 invoke/stream，再追回 response/event。标出异常翻译、id 传递和权限检查。

## WorkAgentHarness 仿写顺序
1. 定义 `AgentInput` / `AgentResult`：用户文本、会话标识、角色/配置引用、结果文本和终态；核心层不依赖 HTTP Request。
2. 设计 Agent 构造层，注入上一章的模型接口；角色/提示配置与模型供应商配置分开。
3. 实现最短执行器：system prompt + user input → model → result，不接持久化与工具。
4. 接一个项目真实入口，由 adapter 把请求转成 `AgentInput`；route 负责协议而非 Agent 业务逻辑。
5. 增加 thread/session 标识，验证两条会话不会共享意外状态；记录哪些状态仍在内存。
6. 再加 stream 输出；复用同一构建和授权逻辑，对比流与非流的终态/错误。

## 分层练习
L1 fake 模型下构造 Agent 并返回固定结果；L2 接入真实聊天入口并装配提示/工具容器；L3 补角色、thread 隔离、流式/非流式；L4 验证空输入、重复请求、模型/构造失败。

## 交付与出口
交付 Agent input/output 契约、入口时序图、真实入口操作记录。你要能讲清一条用户消息如何进入 Agent 图、怎样得到响应，以及哪里开始保存状态。
