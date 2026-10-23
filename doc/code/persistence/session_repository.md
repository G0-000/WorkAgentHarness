# persistence/session_repository.py — 会话与消息仓储

> **源码路径**: `backend/packages/harness/workagentharness/persistence/session_repository.py`
> **对应功能**: WAH-RUN-006

## 顺序执行链

```text
SessionRepository.create(session_id, owner_id)
  │
  └─► INSERT OR IGNORE INTO sessions(...)
        └─► 幂等，重复创建不报错

SessionRepository.add_message(session_id, role, content)
  │
  ├─► INSERT INTO messages(...)
  ├─► UPDATE sessions SET updated_at = ?
  └─► commit

SessionRepository.list_messages(session_id, owner_id)
  │
  └─► SELECT ... FROM messages JOIN sessions
        WHERE session_id = ? AND owner_id = ?
        ORDER BY id
```

## 关键设计

1. **INSERT OR IGNORE**：create 幂等，重复调用不报错。
2. **owner 条件查询**：list_messages 带 owner_id 过滤，避免跨用户读取。
3. **只存业务历史**：不读 LangGraph 内部 checkpoint，两套历史各管各的。

## 边界与待补

- 无分页（全量返回）
- 无消息编辑 / 删除 / 归档
- 无 session 列表查询
