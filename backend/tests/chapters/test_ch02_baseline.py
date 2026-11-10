"""第 2 章验收：仓库基线与快照（篇级，理解 + 命令核对）。

对应教程：二-启动一个可配置可恢复的Agent / 2. 第1篇综合测试与验收。
说明：EvoFlow 仓库不存在时跳过（换机器只跑本项目也能通过其余章节）。
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

EVOFLOW = Path("/Users/main/EvoFlow")
EXPECTED_HEAD = "8e462a37ba584c17feffa8c1bb22c3b53d98a057"


@unittest.skipUnless(EVOFLOW.exists(), "本机没有 EvoFlow 仓库，跳过基线核对")
class BaselineTest(unittest.TestCase):
    def test_head_is_frozen_snapshot(self):
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=EVOFLOW,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(head, EXPECTED_HEAD, "EvoFlow HEAD 已变化，须重新盘点")

    def test_worktree_clean(self):
        # 只要求 EvoFlow 干净；本仓自身允许有未提交改动
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=EVOFLOW,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(status, "", "EvoFlow 工作区不干净，快照读数不可信")


if __name__ == "__main__":
    unittest.main()
