"""第 13 章验收：第 3 篇综合（工具调用 → 截断 → 事件 → SSE → 失败路径）。

对应教程：13. 第3篇综合测试与验收：工具调用与流式交付。
走真实 CLI 子进程，验的是入口而不是函数。
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.chapters.helpers import BACKEND_DIR, cli_command


def run_cli(*args: str, timeout: int = 90) -> subprocess.CompletedProcess:
    return subprocess.run(
        cli_command(*args), cwd=BACKEND_DIR, capture_output=True, text=True, timeout=timeout
    )


class PartThreeEndToEndTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wah-ch13-")
        self.db = str(Path(self._tmp.name) / "e2e.db")

    def tearDown(self):
        self._tmp.cleanup()

    def test_calculator_through_model_and_cli(self):
        proc = run_cli("--config", "config.yaml", "--db", self.db, "--once", "计算 2+3*4")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("工具结果：14", proc.stdout)

    def test_stream_mode_prints_events(self):
        proc = run_cli("--config", "config.yaml", "--db", self.db, "--stream", "--once", "你好")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertRegex(proc.stdout, r"thread=[0-9a-f]{32} run=[0-9a-f]{32}")
        self.assertIn("已收到", proc.stdout)

    def test_sse_mode_three_frames(self):
        proc = run_cli("--config", "config.yaml", "--db", self.db, "--sse", "--once", "你好")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ids = re.findall(r"^id: (\d+)$", proc.stdout, flags=re.M)
        self.assertEqual(ids, ["1", "2", "3"])
        self.assertIn("event: run_start", proc.stdout)
        self.assertIn("event: text_delta", proc.stdout)
        self.assertIn("event: run_end", proc.stdout)

    def test_dangerous_command_guard_through_tool_layer(self):
        # 走工具层而不是解析层：模型不参与，直接验宿主护栏
        from workagentharness.tools.host_direct.terminal_tool import terminal_tool
        out = terminal_tool.invoke({"command": "rm -rf /"})
        self.assertTrue(out.startswith("[DangerousCommand]"), out)


if __name__ == "__main__":
    unittest.main()
