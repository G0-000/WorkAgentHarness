"""Run 状态的有限状态转移。

一次用户消息触发一次 Agent 执行，就是一条 run。
状态机只有四个状态，运行中只有一个入口，终态只有一个出口：

    start()          running
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   complete()      fail()         cancel()
   completed       failed         cancelled

同一 run 只允许从 running 变一次终态；重复或并发的第二次写入必须失败，
不能出现"既 completed 又 failed"的记录。
"""

import sqlite3


class RunRepository:
    """封装 run 表写入；只允许一个 running run 结束一次。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        # 复用外部传入的连接：业务表与 checkpoint 表共用一个 .db 文件
        self._conn = conn

    def start(self, run_id: str, session_id: str, owner_id: str, now: str) -> None:
        """插入一条 running 记录。

        run_id 每次执行新生成，重试不复用旧 id——复用会让两条执行共用一个状态，
        无法区分哪次失败、哪次成功。
        """
        self._conn.execute(
            "INSERT INTO runs(id, session_id, owner_id, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'running', ?, ?)",
            (run_id, session_id, owner_id, now, now),
        )
        self._conn.commit()  # 每方法独立提交，不和消息写入组成跨表事务（见 5.1 已知缺口）

    def finish(self, run_id: str, status: str, now: str, error_code: str = "") -> None:
        """把 running 推进到终态；重复或并发调用只有第一次能成功。"""
        if status not in {"completed", "failed", "cancelled"}:
            # running 是起始态不是终态，不允许用它作为 finish 的目标
            raise ValueError(f"非法 run 终态: {status}")

        cursor = self._conn.execute(
            # `AND status = 'running'` 是关键：条件更新保证只有仍在运行的 run 会被改写
            "UPDATE runs SET status = ?, error_code = ?, updated_at = ? "
            "WHERE id = ? AND status = 'running'",
            (status, error_code, now, run_id),
        )
        self._conn.commit()

        if cursor.rowcount != 1:
            # rowcount=0 有两种可能：run id 不存在，或已被另一个回调先置成终态。
            # 两种情况都不能静默放过，否则会把"重复结束"伪装成成功。
            raise RuntimeError(f"run 不存在或已经结束: {run_id}")

    def complete(self, run_id: str, now: str) -> None:
        """成功收尾：Agent 正常返回并写完 assistant 消息。"""
        self.finish(run_id, "completed", now)

    def cancel(self, run_id: str, now: str) -> None:
        """取消收尾（KeyboardInterrupt）。

        注意：这里只把库状态置成 cancelled，并不负责让模型请求、工具或后台进程真正停下；
        "标记已取消"和"真正中断"是两件事（见 5.1 取消边界）。
        """
        self.finish(run_id, "cancelled", now)

    def fail(self, run_id: str, error_code: str, now: str) -> None:
        """失败收尾。

        error_code 传异常类名（如 ValueError），不传异常原文：
        str(exc) 可能带请求内容甚至密钥片段，不适合原样入库。
        """
        self.finish(run_id, "failed", now, error_code)
