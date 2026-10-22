# 第 4 章｜消息、会话、Checkpoint、Run 与分享

> 所属篇：启动一个可配置、可恢复的 Agent
> 功能范围：`WAH-RUN-005–006、WAH-RUN-010`
> 导航：[教程册总目录](../README.md) · [本篇导读](README.md) · [课程索引](../../学习手册/课程目录.md) · [功能路线](../../学习手册/功能单元路线.md) · [唯一状态清单](../../学习手册/功能清单.md)

## 本章要做出的东西
把 session、thread、消息历史、checkpoint、run、share 分清楚。每类对象有自己的所有者、生命周期和读写方；不能都叫“聊天记录”。

## EvoFlow 阅读顺序
1. 读 `chat_sessions.py`、`sessions.py`、`threads.py`，追 session/thread 创建、复用和身份归属。
2. 读 `persistence/chat_session_service.py`、`session_repositories.py`、`chat_message_repositories.py`，画实体关系、主键、排序、分页、删除。
3. 读 `agents/checkpointer/` 和 checkpointer 配置，确认 checkpoint key、保存触发点和恢复点；它不替代业务消息表。
4. 读 `runs.py`、`live_run_repositories.py`、`session_run_state.py`，画 run 状态机及取消、事件、终态同步。
5. 读 `share.py`、`chat_share_repositories.py`、`client_presence.py`、`session_notifications.py`，确认分享访问范围、在线状态、通知的创建/过期/撤销。
6. 对照 Web 页面如何加载历史、恢复 stream、继续 run、查看分享页；将前端 API 对上 route。

## WorkAgentHarness 仿写顺序
1. 先写领域词汇和 ER 图：Conversation/Session、Thread、Message、Run、Checkpoint、Share 的关系与 owner。
2. 用内存 repository 实现“创建 session→保存两条消息→分页读取”。
3. 为 Run 定状态机，定义允许的状态转换和唯一终态；并发重复更新不能造成两个终态。
4. 加数据库迁移和 repository，再接真实入口；用两个用户验证所有权隔离。
5. 接 checkpoint 时用明确 thread key 关联，重启后证明 Agent 状态恢复与业务历史查询是两条职责。
6. 最后做分享、归档/删除、通知和在线状态，定义删 session 对消息/checkpoint/share 的级联策略。

## 分层练习与出口
L1 内存保存/读取消息和 run；L2 真实历史、通知和在线状态入口；L3 覆盖 session/thread/checkpoint/run/share/归档删除；L4 进程重启、权限隔离、并发写。用 A/B 用户和两个 session 复现完整生命周期，交付 ER 图、状态机和重启恢复记录。
