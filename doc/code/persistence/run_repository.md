# persistence/run_repository.py — Run 状态机仓储

> **源码路径**: `backend/packages/harness/workagentharness/persistence/run_repository.py`
> **对应功能**: WAH-RUN-007

## 状态转移图

```text
        start()
          │
          ▼
       running ────── complete() ────► completed
          │
          ├────────── fail() ───────► failed
          │
          └────────── cancel() ──────► cancelled
```

## 顺序执行链

```text
RunRepository.start(run_id, session_id, owner_id, now)
  │
  └─► INSERT INTO runs(..., status='running', ...)

RunRepository.finish(run_id, status, now, error_code='')
  │
  ├─► 校验 status ∈ {completed, failed, cancelled}
  │
  ├─► UPDATE runs SET status=?, error_code=?, updated_at=?
  │     WHERE id=? AND status='running'
  │
  └─► rowcount != 1 → raise RuntimeError
        └─► 防重复结束 / run 不存在
```

## 关键设计

1. **只允许 running → 终态**：`WHERE status='running'` 条件防重复转移。
2. **一行一状态转移**：每次 finish 都是原子操作，不会出现两个终态。
3. **三个便捷方法**：complete / cancel / fail 都是 finish 的封装。

## 边界与待补

- 无 run 列表 / 查询接口
- 无运行时长统计
- 无并发 run 计数
