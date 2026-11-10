"""按章跑验收测试：一章一个文件，输出「章 / 用例 / 通过 / 失败」。

用法（在 backend 下）：
    uv run --project packages/harness python tests/run_chapter_tests.py
    uv run --project packages/harness python tests/run_chapter_tests.py 3 5

约定：
    - 只有"已学习且已实现"的章才有测试文件；
    - 第 1 章是理解验收（阅读 + 基线表），没有可执行断言，不生成测试；
    - 第 14 章以后没有实现代码，一个测试文件都不应存在。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

CHAPTERS: dict[int, str | None] = {
    1: None,  # 理解验收：无代码可测
    2: "tests.chapters.test_ch02_baseline",
    3: "tests.chapters.test_ch03_config",
    4: "tests.chapters.test_ch04_agent",
    5: "tests.chapters.test_ch05_persistence",
    6: "tests.chapters.test_ch06_lifecycle",
    7: "tests.chapters.test_ch07_part2_e2e",
    8: "tests.chapters.test_ch08_catalog",
    9: "tests.chapters.test_ch09_tools",
    10: "tests.chapters.test_ch10_background",
    11: "tests.chapters.test_ch11_middleware",
    12: "tests.chapters.test_ch12_events",
    13: "tests.chapters.test_ch13_part3_e2e",
}


def main(argv: list[str]) -> int:
    targets = [int(arg) for arg in argv[1:]] or list(CHAPTERS)
    failures = 0
    print(f"{'章':>3} | {'用例':>4} | {'通过':>4} | {'失败':>4} | 结果")
    print("-" * 52)
    for chapter in targets:
        module_name = CHAPTERS.get(chapter)
        if module_name is None:
            print(f"{chapter:>3} |    0 |    0 |    0 | 理解验收（无测试代码）")
            continue
        suite = unittest.defaultTestLoader.loadTestsFromName(module_name)
        result = unittest.TextTestRunner(stream=open("/dev/null", "w"), verbosity=0).run(suite)
        total = result.testsRun
        failed = len(result.failures) + len(result.errors) + len(result.skipped)
        failures += failed
        status = "通过" if failed == 0 else "失败"
        print(f"{chapter:>3} | {total:>4} | {total - failed:>4} | {failed:>4} | {status}")
        for case, trace in result.failures + result.errors:
            print(f"      ✗ {case}\n{trace.strip().splitlines()[-1]}")
        for case, reason in result.skipped:
            print(f"      - 跳过 {case}: {reason}")
    print("-" * 52)
    print("全部通过" if failures == 0 else f"存在失败：{failures} 项")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
