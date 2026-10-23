# persistence/ — 业务持久化层

> **源码路径**: `backend/packages/harness/workagentharness/persistence/`
> **对应功能**: WAH-RUN-006 聊天记录与存储、WAH-RUN-007 Run 状态

## 文件清单

| 文件 | 职责 |
|---|---|
| `schema.py` | 建表 SQL：sessions / messages / runs |
| `db.py` | 打开 SQLite 连接、设置 WAL、执行建表 |
| `session_repository.py` | Session + Message 读写 |
| `run_repository.py` | Run 状态机：start → complete / fail / cancel |
