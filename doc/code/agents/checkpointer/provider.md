# agents/checkpointer/provider.py — SQLite Checkpoint Provider

> **源码路径**: `backend/packages/harness/workagentharness/agents/checkpointer/provider.py`
> **对应功能**: WAH-RUN-005

## 顺序执行链

```text
open_checkpointer(db_path: str)
  │
  ├─► Path(db_path).parent.mkdir(exist_ok=True)
  │     └─► 确保目录存在
  │
  ├─► sqlite3.connect(db_path, check_same_thread=False)
  │     └─► 允许多线程访问
  │
  ├─► PRAGMA journal_mode=WAL
  │     └─► 支持并发读写，不锁库
  │
  ├─► SqliteSaver(conn)
  │
  ├─► saver.setup()
  │     └─► 由 LangGraph 建 checkpoint 表
  │
  └─► return (conn, saver)
        └─► 调用方负责最终 conn.close()
```

## 关键设计

1. **WAL 模式**：Checkpoint 写入和业务库写入可以并发不阻塞。
2. **连接由入口统一关闭**：本函数只打开不关闭，避免资源泄漏。
3. **setup() 幂等**：`CREATE TABLE IF NOT EXISTS`，重复调用不会报错。

## 边界与待补

- Checkpoint 和业务库共用同一个 .db 文件，后续建议拆分
- 无 Checkpoint 过期清理
- 无并发冲突处理（同 thread 并发写）
- 无版本兼容 / 迁移
