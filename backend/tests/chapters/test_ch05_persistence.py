"""第 5 章验收：会话/消息/run 三表、checkpoint 表与跨轮恢复（WAH-RUN-005/006/010）。

对应教程：5. 消息会话CheckpointRun与分享。
重点区分：业务三表（可查询历史）≠ checkpoint 表（图状态恢复）。
"""

from __future__ import annotations

import unittest

from tests.chapters.helpers import ServiceBundle


class PersistenceTest(unittest.TestCase):
    def setUp(self):
        self.bundle = ServiceBundle(with_tools=False)

    def tearDown(self):
        self.bundle.close()

    def _tables(self) -> set[str]:
        rows = self.bundle.database.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return {row["name"] for row in rows}

    def test_business_tables_created(self):
        self.assertTrue({"sessions", "messages", "runs"} <= self._tables())

    def test_checkpoint_tables_created_in_same_file(self):
        # 同一个 .db 文件里还有 LangGraph 自己的表，写入者是 saver.setup()
        self.assertTrue({"checkpoints", "writes"} <= self._tables())

    def test_message_order_and_owner_isolation(self):
        sessions = self.bundle.sessions
        sessions.create("s1", "local-user")
        sessions.add_message("s1", "user", "第一句")
        sessions.add_message("s1", "assistant", "第二句")
        rows = sessions.list_messages("s1", "local-user")
        self.assertEqual([row["content"] for row in rows], ["第一句", "第二句"])
        # 换一个 owner 读不到：JOIN + owner_id 校验生效
        self.assertEqual(sessions.list_messages("s1", "someone-else"), [])

    def test_run_lifecycle_and_growth(self):
        result = self.bundle.run_once("你好")
        self.assertEqual(result.status, "completed")
        counts = {
            table: self.bundle.database.execute(
                f"SELECT COUNT(*) AS c FROM {table}"
            ).fetchone()["c"]
            for table in ("messages", "runs", "sessions")
        }
        self.assertEqual(counts, {"messages": 2, "runs": 1, "sessions": 1})

        second = self.bundle.service.execute("local-user", "s1", "再来一句")
        self.assertIn("第 2 轮", second.answer)  # checkpoint 恢复了历史
        self.assertEqual(
            self.bundle.database.execute("SELECT COUNT(*) AS c FROM runs").fetchone()["c"], 2
        )

    def test_run_status_persisted_as_completed(self):
        result = self.bundle.run_once("你好")
        row = self.bundle.database.execute(
            "SELECT status, error_code FROM runs WHERE id = ?", (result.run_id,)
        ).fetchone()
        self.assertEqual((row["status"], row["error_code"]), ("completed", ""))


if __name__ == "__main__":
    unittest.main()
