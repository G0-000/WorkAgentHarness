"""第 7 章验收：第 2 篇综合（配置 → 单轮 → 恢复 → 落库 → 入口）。

对应教程：7. 第2篇综合测试与验收：配置到恢复全链路。
全部走真实 CLI 子进程，不直接调函数——验的是"用户敲命令能不能得到这个结果"。
"""

from __future__ import annotations

import re
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.chapters.helpers import BACKEND_DIR, cli_command


def run_cli(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        cli_command(*args), cwd=BACKEND_DIR, capture_output=True, text=True, timeout=timeout
    )


class PartTwoEndToEndTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wah-ch7-")
        self.db = str(Path(self._tmp.name) / "e2e.db")

    def tearDown(self):
        self._tmp.cleanup()

    def test_once_mode_prints_thread_and_answer(self):
        proc = run_cli("--config", "config.yaml", "--db", self.db, "--once", "你好")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertRegex(proc.stdout, r"thread=[0-9a-f]{32} run=[0-9a-f]{32}")
        self.assertIn("助手> 已收到（第 1 轮）：你好", proc.stdout)

    def test_same_thread_second_round_and_db_counts(self):
        first = run_cli("--config", "config.yaml", "--db", self.db, "--once", "第一句")
        session = re.search(r"thread=([0-9a-f]{32})", first.stdout).group(1)
        second = run_cli(
            "--config", "config.yaml", "--db", self.db, "--thread", session, "--once", "第二句"
        )
        self.assertIn("第 2 轮", second.stdout)

        conn = sqlite3.connect(self.db)
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("sessions", "messages", "runs")
        }
        conn.close()
        self.assertEqual(counts, {"sessions": 1, "messages": 4, "runs": 2})

    def test_help_lists_seven_arguments(self):
        proc = run_cli("--help")
        self.assertEqual(proc.returncode, 0)
        for flag in ("--config", "--db", "--thread", "--once", "--stream", "--sse", "--mode"):
            self.assertIn(flag, proc.stdout)

    def test_bad_config_fails_loudly(self):
        bad = Path(self._tmp.name) / "bad.yaml"
        bad.write_text("models:\n  chat:\n    provider: fake\n", encoding="utf-8")
        proc = run_cli("--config", str(bad), "--db", self.db, "--once", "你好")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("models.chat 配置字段无效", proc.stderr)


if __name__ == "__main__":
    unittest.main()
