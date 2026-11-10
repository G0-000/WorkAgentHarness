"""第 10 章 10.1 验收：后台命令、输出截断与超时上限（WAH-TOOL-010 部分）。

10.2（Browser Bridge / Computer Use）在本仓没有实现代码，因此没有测试：
测试文件的存在本身不能当作"已实现"的证据。
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from workagentharness.tools.host_direct.terminal_tool import (
    _format_subprocess_output, _foreground_timeout, _should_auto_background,
    _spawn_background, _strip_ansi, terminal_tool,
)


class BackgroundHeuristicsTest(unittest.TestCase):
    def test_long_running_patterns(self):
        for command in ("npm install", "pytest -q", "uvicorn app:main", "tail -f x.log"):
            self.assertTrue(_should_auto_background(command, False), command)
        self.assertFalse(_should_auto_background("echo hi", False))

    def test_explicit_background_flag_wins(self):
        self.assertFalse(_should_auto_background("npm install", True))

    def test_timeout_clamped_to_120(self):
        self.assertEqual(_foreground_timeout("x", 500, explicit_timeout=True), 120)
        self.assertEqual(_foreground_timeout("x", 0, explicit_timeout=False), 1)

    def test_output_truncation_keeps_head_and_tail(self):
        text = _format_subprocess_output("A" * 5000 + "B" * 5000, "", 0)
        self.assertIn("已截断", text)
        self.assertLess(len(text), 8100)
        self.assertTrue(text.startswith("A"))
        self.assertTrue(text.endswith("B"))

    def test_ansi_stripped(self):
        self.assertEqual(_strip_ansi("\x1b[31mred\x1b[0m"), "red")


class BackgroundSpawnTest(unittest.TestCase):
    def test_spawn_returns_pid_and_log(self):
        # 在临时目录里跑，日志文件落在临时目录，不污染仓库 data/
        old = Path.cwd()
        with tempfile.TemporaryDirectory(prefix="wah-ch10-") as tmp:
            try:
                import os
                os.chdir(tmp)
                pid, log_path = _spawn_background("echo background-ok", None)
                self.assertTrue(pid.isdigit())
                self.assertTrue(log_path.exists())
                # 后台进程写日志有延迟，轮询等待而不是固定 sleep
                for _ in range(50):
                    if "background-ok" in log_path.read_text(encoding="utf-8"):
                        break
                    import time
                    time.sleep(0.05)
                self.assertIn("background-ok", log_path.read_text(encoding="utf-8"))
            finally:
                os.chdir(old)

    def test_tool_with_background_true(self):
        out = terminal_tool.invoke({"command": "echo bg", "background": True})
        self.assertTrue(out.startswith("[Background]"), out)


if __name__ == "__main__":
    unittest.main()
