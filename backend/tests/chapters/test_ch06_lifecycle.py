"""第 6 章验收：run 状态机、失败/取消终态与 stdio 入口（WAH-RUN-007/008/009、API-009）。

对应教程：6. 运行生命周期取消和多进程入口。
"""

from __future__ import annotations

import io
import json
import unittest

from tests.chapters.helpers import ServiceBundle
from workagentharness.app_server.stdio_rpc import serve_stdio
from workagentharness.persistence.run_repository import RunRepository


class ExplodingAgent:
    """真实 Agent 替身：只用于制造失败路径，不参与成功路径。"""

    def invoke(self, *_args, **_kwargs):
        raise ValueError("boom")


class RunStateMachineTest(unittest.TestCase):
    def setUp(self):
        self.bundle = ServiceBundle(with_tools=False)

    def tearDown(self):
        self.bundle.close()

    def test_double_finish_raises(self):
        self.bundle.sessions.create("s1", "local-user")  # runs.session_id 有外键，先建会话
        runs = RunRepository(self.bundle.database)
        runs.start("r1", "s1", "local-user", "now")
        runs.complete("r1", "now")
        with self.assertRaises(RuntimeError) as ctx:
            runs.fail("r1", "ValueError", "now")
        self.assertIn("已经结束", str(ctx.exception))

    def test_illegal_terminal_status(self):
        self.bundle.sessions.create("s1", "local-user")
        runs = RunRepository(self.bundle.database)
        runs.start("r2", "s1", "local-user", "now")
        with self.assertRaises(ValueError) as ctx:
            runs.finish("r2", "running", "now")
        self.assertEqual(str(ctx.exception), "非法 run 终态: running")

    def test_agent_failure_becomes_failed_run(self):
        service = self.bundle.service
        service._agent = ExplodingAgent()  # 只替换 agent，service 生命周期逻辑保持真实
        self.bundle.sessions.create("s1", "local-user")
        result = service.execute("local-user", "s1", "你好")
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "ValueError")  # 存类型名，不存异常原文
        row = self.bundle.database.execute(
            "SELECT status, error_code FROM runs WHERE id = ?", (result.run_id,)
        ).fetchone()
        self.assertEqual((row["status"], row["error_code"]), ("failed", "ValueError"))

    def test_keyboard_interrupt_marks_cancelled(self):
        service = self.bundle.service

        class InterruptingAgent:
            def invoke(self, *_args, **_kwargs):
                raise KeyboardInterrupt

        service._agent = InterruptingAgent()
        self.bundle.sessions.create("s1", "local-user")
        with self.assertRaises(KeyboardInterrupt):
            service.execute("local-user", "s1", "你好")
        row = self.bundle.database.execute(
            "SELECT status FROM runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(row["status"], "cancelled")

    def test_empty_input_rejected_before_run(self):
        with self.assertRaises(ValueError):
            self.bundle.service.execute("local-user", "s1", "   ")
        count = self.bundle.database.execute("SELECT COUNT(*) AS c FROM runs").fetchone()["c"]
        self.assertEqual(count, 0)


class StdioRpcTest(unittest.TestCase):
    def setUp(self):
        self.bundle = ServiceBundle(with_tools=False)

    def tearDown(self):
        self.bundle.close()

    def _call(self, requests: list[dict]) -> list[dict]:
        stdin = io.StringIO("\n".join(json.dumps(item, ensure_ascii=False) for item in requests) + "\n")
        stdout = io.StringIO()
        serve_stdio(self.bundle.service, self.bundle.sessions, stdin=stdin, stdout=stdout)
        return [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]

    def test_initialize_and_ping(self):
        replies = self._call([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "server/ping", "params": {}},
        ])
        self.assertEqual(replies[0]["result"]["serverInfo"]["name"], "WorkAgentHarness")
        self.assertEqual(replies[0]["result"]["capabilities"], {"turnStart": True})
        self.assertEqual(replies[1]["result"], {"ok": True})

    def test_turn_start_runs_service(self):
        reply = self._call([{
            "jsonrpc": "2.0", "id": 3, "method": "turn/start",
            "params": {"sessionId": "sid-1", "text": "你好"},
        }])[0]
        self.assertEqual(reply["result"]["status"], "completed")
        self.assertEqual(reply["result"]["answer"], "已收到（第 1 轮）：你好")
        self.assertEqual(
            self.bundle.database.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"], 1
        )

    def test_unknown_method_and_bad_json(self):
        stdin = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 9, "method": "nope"}) + "\n"
            + "{not json}\n"
        )
        stdout = io.StringIO()
        serve_stdio(self.bundle.service, self.bundle.sessions, stdin=stdin, stdout=stdout)
        replies = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(replies[0]["error"]["code"], -32601)
        self.assertEqual(replies[1]["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()
