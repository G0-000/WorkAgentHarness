# persistence/db.py — 数据库连接初始化

> **源码路径**: `backend/packages/harness/workagentharness/persistence/db.py`
> **对应功能**: WAH-RUN-006

## 顺序执行链

```text
open_database(db_path: str)
  │
  ├─► Path(db_path).parent.mkdir(exist_ok=True)
  │
  ├─► sqlite3.connect(db_path, check_same_thread=False)
  │
  ├─► conn.row_factory = sqlite3.Row
  │     └─► 查询结果支持按列名访问
  │
  ├─► PRAGMA journal_mode=WAL
  │
  ├─► PRAGMA foreign_keys=ON
  │     └─► 开启外键约束
  │
  ├─► conn.executescript(SCHEMA_SQL)
  │     └─► 幂等建表
  │
  ├─► conn.commit()
  │
  └─► return conn
```

## 关键设计

1. **WAL + 外键双开**：读写并发 + 数据完整性。
2. **row_factory = Row**：Repository 里查出来可以 `row["column_name"]` 访问。
3. **幂等建表**：`CREATE TABLE IF NOT EXISTS`，重复启动不报错。

## 边界与待补

- 无数据库迁移（schema 变更靠手动）
- 无连接池（单连接）
