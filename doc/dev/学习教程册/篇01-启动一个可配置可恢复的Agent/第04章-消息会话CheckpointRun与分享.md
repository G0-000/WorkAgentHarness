# 第 4 章｜消息、会话、Checkpoint、Run 与分享

> 所属篇：启动一个可配置、可恢复的 Agent
> 功能范围：`WAH-RUN-005–006、WAH-RUN-010`
> 导航：[教程册总目录](../README.md) · [本篇导读](README.md) · [课程索引](../../学习手册/课程目录.md) · [功能路线](../../学习手册/功能单元路线.md) · [唯一状态清单](../../学习手册/功能清单.md)

## 本章要做出的东西
把 session、thread、消息历史、checkpoint、run、share 分清楚。每类对象有自己的所有者、生命周期和读写方；不能都叫“聊天记录”。

## 本章总流程与小节

本章沿“创建 session → 接收消息 → 写业务历史 → 以 thread_id 调 Agent → checkpoint 保存/恢复 → 写 run 终态”追踪。分享属于独立生命周期，不能混成 checkpoint。章节正文是总流程；具体功能如下：

| 小节 | 具体功能 | 代码入口 | 说明文档 |
|---|---|---|---|
| 第 1 节 | Session、消息表和业务历史 Repository | `persistence/schema.py`、`db.py`、`session_repository.py` | [业务会话和消息怎样存取](第04章-消息会话CheckpointRun与分享/第01节-会话和业务消息存储.md) |
| 第 2 节 | LangGraph checkpoint 与 thread 恢复 | `agents/checkpointer/provider.py`、`agents/lead_agent/agent.py` | [Checkpoint 保存什么，怎样恢复](第04章-消息会话CheckpointRun与分享/第02节-Checkpoint与Thread恢复.md) |
| 第 3 节 | Share API、访问范围与生命周期 | 当前尚无实现 | [分享行为的边界和未实现验收项](第04章-消息会话CheckpointRun与分享/第03节-分享生命周期.md) |

源码位置按仓库根目录相对路径；未实现的功能只解释目标与验收标准，不会伪造已完成代码。

## EvoFlow 阅读顺序
1. 读 EvoFlow 仓库根目录的 `backend/app/gateway/routers/chat_sessions.py`、`sessions.py`、`threads.py`，追 session/thread 创建、复用和身份归属。
2. 读 `backend/packages/harness/evoflow/persistence/chat_session_service.py`、`session_repositories.py`、`chat_message_repositories.py`，画实体关系、主键、排序、分页、删除。
3. 读 `backend/packages/harness/evoflow/agents/checkpointer/` 和 checkpointer 配置，确认 checkpoint key、保存触发点和恢复点；它不替代业务消息表。
4. 读 `backend/app/gateway/routers/runs.py`、`backend/packages/harness/evoflow/persistence/live_run_repositories.py`、`session_run_state.py`，画 run 状态机及取消、事件、终态同步。
5. 读 `backend/app/gateway/routers/share.py`、`backend/packages/harness/evoflow/persistence/chat_share_repositories.py`、`backend/app/gateway/client_presence.py`、`backend/packages/harness/evoflow/persistence/session_notification_repositories.py`，确认分享访问范围、在线状态、通知的创建/过期/撤销。
6. 对照 Web 页面如何加载历史、恢复 stream、继续 run、查看分享页；将前端 API 对上 route。

## AgentFlow 第一遍复盘

对照 AgentFlow 的 `agents/checkpointer/provider.py`、`persistence/session_repositories.py`、`persistence/schema.py` 和 `backend/app/gateway/routers/runs.py`，分别记录框架 checkpoint 与业务历史的实现。AgentFlow 第一遍把 session/thread 与消息 repo 合并在 `SessionRepository`，没有 EvoFlow 那套分享/通知完整行为；把它们列为“第一遍缺口”，继续回到 EvoFlow 的 `backend/app/gateway/routers/`、`backend/packages/harness/evoflow/persistence/` 和 `session_execution/` 追证据，不能用 AgentFlow 缺失证明 EvoFlow 不支持。

## WorkAgentHarness 仿写顺序
1. 先写领域词汇和 ER 图：Conversation/Session、Thread、Message、Run、Checkpoint、Share 的关系与 owner。
2. 用内存 repository 实现“创建 session→保存两条消息→分页读取”。
3. 为 Run 定状态机，定义允许的状态转换和唯一终态；并发重复更新不能造成两个终态。
4. 加数据库迁移和 repository，再接真实入口；用两个用户验证所有权隔离。
5. 接 checkpoint 时用明确 thread key 关联，重启后证明 Agent 状态恢复与业务历史查询是两条职责。
6. 最后做分享、归档/删除、通知和在线状态，定义删 session 对消息/checkpoint/share 的级联策略。

## 分层练习与出口
L1 内存保存/读取消息和 run；L2 真实历史、通知和在线状态入口；L3 覆盖 session/thread/checkpoint/run/share/归档删除；L4 进程重启、权限隔离、并发写。用 A/B 用户和两个 session 复现完整生命周期，交付 ER 图、状态机和重启恢复记录。

## 跟着写代码：业务历史与图状态分开存

这里建立两种存储：`SessionRepository` 负责 UI/API 查询的业务会话和消息；LangGraph checkpointer 负责恢复 Agent 内部状态。不要试图从 checkpoint 表直接拼聊天列表。

### 1. 建立业务表：`persistence/schema.py`

```python
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,               -- 稳定 session/thread 标识
    owner_id TEXT NOT NULL,             -- 所属用户；即使本地版也先保留身份边界
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,                 -- 一次执行一个 id；重试时创建新 id
    session_id TEXT NOT NULL REFERENCES sessions(id),
    owner_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    error_code TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""
```

表里保存业务可查询的数据。Checkpoint 是另一套框架管理的数据，不要在这个 SQL 里手工创建 LangGraph 的内部表。

### 2.1 初始化数据库连接：`persistence/db.py`

```python
import sqlite3
from pathlib import Path

from workagentharness.persistence.schema import SCHEMA_SQL


def open_database(db_path: str) -> sqlite3.Connection:
    """打开业务 SQLite，并统一设置外键与行读取方式。"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)  # 首次运行创建 data/ 目录
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row                         # 查询结果可按列名读取
    conn.execute("PRAGMA journal_mode=WAL")                # 允许读写并发
    conn.execute("PRAGMA foreign_keys=ON")                 # 让 REFERENCES 真正生效
    conn.executescript(SCHEMA_SQL)                          # 只初始化业务 schema
    conn.commit()
    return conn                                             # 调用方负责 close()
```

### 3. 用 Repository 收口 SQL：`persistence/session_repository.py`

```python
import sqlite3
from datetime import UTC, datetime


def now_utc() -> str:
    """统一使用 UTC ISO 时间，避免不同机器的本地时区混入排序字段。"""
    return datetime.now(UTC).isoformat()


class SessionRepository:
    """只负责 session 和业务消息读写，不负责运行 Agent。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn  # 连接生命周期由应用装配层负责

    def create(self, session_id: str, owner_id: str) -> None:
        stamp = now_utc()
        self._conn.execute(
            "INSERT OR IGNORE INTO sessions(id, owner_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, owner_id, stamp, stamp),  # 参数化 SQL，禁止拼接输入
        )
        self._conn.commit()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self._conn.execute(
            "INSERT INTO messages(session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, now_utc()),
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now_utc(), session_id),
        )
        self._conn.commit()

    def list_messages(self, session_id: str, owner_id: str) -> list[sqlite3.Row]:
        # JOIN 同时验证 owner，不能只凭猜到的 session_id 读取私有消息。
        return list(self._conn.execute(
            "SELECT m.id, m.role, m.content, m.created_at "
            "FROM messages AS m JOIN sessions AS s ON s.id = m.session_id "
            "WHERE m.session_id = ? AND s.owner_id = ? ORDER BY m.id",
            (session_id, owner_id),
        ))
```

注意：此教学版本每个方法提交一次，方便看清数据变化；真正组合“一条用户消息、一条 Agent 回复和一个 run”时，需要在应用服务层使用一个事务，避免只写入半轮对话。

### 4. 让 Agent 接收 Checkpointer

在第 3 章的 `make_lead_agent` 上增加可选参数，不重写 Agent：

```python
def make_lead_agent(model, *, checkpointer=None, system_prompt=DEFAULT_SYSTEM_PROMPT):
    """第 3 章单轮和第 4 章持久化复用同一个构造入口。"""
    return create_agent(
        model=model,
        tools=[],
        middleware=[],
        checkpointer=checkpointer,  # None 表示不恢复；传 saver 后按 thread_id 恢复
        system_prompt=system_prompt,
    )
```

### 5. 接入 SQLite Checkpointer：`agents/checkpointer/provider.py`

```python
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


def open_checkpointer(db_path: str) -> tuple[sqlite3.Connection, SqliteSaver]:
    """打开持久连接并初始化 LangGraph checkpoint 表。"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    saver = SqliteSaver(conn)
    saver.setup()  # 由 saver 创建/维护它自己的 checkpoint schema
    return conn, saver
```

连接由调用方持有并在进程退出时关闭；不要在 Agent 构造函数里偷偷打开连接，否则很难管理测试、重启和多入口生命周期。

### 6. 同一个 thread 恢复图状态

```python
agent = make_lead_agent(model, checkpointer=saver)  # 第 3 章的构造函数增加此参数
repo.create(session_id="local-demo", owner_id="local-user")

config = {"configurable": {"thread_id": "local-demo"}}  # checkpoint 的恢复键
repo.add_message("local-demo", "user", "我叫小林。")
first = agent.invoke({"messages": [("user", "我叫小林。")]}, config=config)
repo.add_message("local-demo", "assistant", str(first["messages"][-1].content))

# 第二次使用相同 thread_id，LangGraph 从 checkpoint 恢复对话状态。
second = agent.invoke({"messages": [("user", "我叫什么？")]}, config=config)
```

这只是单机学习路径。接真实 API 前还要加 run id、事务边界、并发控制、owner 鉴权、分享令牌、删除策略和迁移版本；不能把上面的几行直接视为完整会话系统。
