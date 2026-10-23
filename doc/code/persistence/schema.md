# persistence/schema.py — 业务表 Schema

> **源码路径**: `backend/packages/harness/workagentharness/persistence/schema.py`
> **对应功能**: WAH-RUN-006、WAH-RUN-007

## 表结构

```text
sessions
  ├─ id          TEXT PRIMARY KEY     # thread_id / session_id
  ├─ owner_id    TEXT NOT NULL        # 当前硬编码 "local-user"
  ├─ title       TEXT DEFAULT ''
  ├─ created_at  TEXT NOT NULL
  └─ updated_at  TEXT NOT NULL

messages
  ├─ id          INTEGER PK AUTOINCREMENT
  ├─ session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE
  ├─ role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool'))
  ├─ content     TEXT NOT NULL
  └─ created_at  TEXT NOT NULL

runs
  ├─ id          TEXT PRIMARY KEY
  ├─ session_id  TEXT NOT NULL REFERENCES sessions(id)
  ├─ owner_id    TEXT NOT NULL
  ├─ status      TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled'))
  ├─ error_code  TEXT NOT NULL DEFAULT ''
  ├─ created_at  TEXT NOT NULL
  └─ updated_at  TEXT NOT NULL
```

## 关键设计

1. **外键级联删除**：删 session 时自动删 messages。
2. **CHECK 约束**：role / status 只能取枚举值，数据库层兜底。
3. **时间用 ISO 字符串**：TEXT 存 UTC ISO 8601，不依赖 SQLite 时间函数。

## 边界与待补

- 无索引（messages.session_id 未建索引，数据量大了会慢）
- 无迁移版本号
