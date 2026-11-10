"""第 8 章验收：工具目录、别名、schema 与结果截断协议（WAH-TOOL-001/002）。

对应教程：8. 工具目录Schema与结果协议。
"""

from __future__ import annotations

import unittest

from langchain_core.tools import tool

from workagentharness.tools.builtins import default_catalog
from workagentharness.tools.result import MAX_RESULT_CHARS, shape_result


@tool
def placeholder(query: str) -> str:
    """测试用占位工具。"""
    return query


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.catalog = default_catalog()

    def test_default_tools_and_aliases(self):
        self.assertEqual(self.catalog.names(), ["calculator", "list_directory", "read_text_file", "terminal"])
        self.assertEqual(self.catalog.resolve("calc").name, "calculator")
        self.assertEqual(self.catalog.resolve("ls").name, "list_directory")
        self.assertEqual(self.catalog.resolve("shell").name, "terminal")

    def test_tier_layering(self):
        tiers = {entry["name"]: entry["tier"] for entry in self.catalog.describe_all()}
        self.assertEqual(
            tiers,
            {"calculator": "core", "read_text_file": "workspace",
             "list_directory": "workspace", "terminal": "host"},
        )

    def test_describe_and_schemas_are_model_visible(self):
        schemas = {item["name"]: item for item in self.catalog.schemas()}
        self.assertEqual(set(schemas), set(self.catalog.names()))
        self.assertIn("expression", schemas["calculator"]["args"]["properties"])

    def test_duplicate_registration_rejected(self):
        self.catalog.register(placeholder)  # 先注册一次，第二次才算重名
        with self.assertRaises(ValueError) as ctx:
            self.catalog.register(placeholder)
        self.assertIn("拒绝重复注册", str(ctx.exception))

    def test_alias_conflict_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.catalog.register(placeholder, aliases=("calc",))
        self.assertEqual(str(ctx.exception), "别名冲突: calc")

    def test_unknown_tool_keyerror(self):
        with self.assertRaises(KeyError):
            self.catalog.get("nonexistent")

    def test_result_truncation_at_8000(self):
        shaped = shape_result("big", ok=True, content="x" * 9000)
        self.assertTrue(shaped.truncated)
        self.assertLessEqual(len(shaped.content), MAX_RESULT_CHARS + 40)
        self.assertIn("已截断", shaped.content)
        small = shape_result("small", ok=True, content="ok")
        self.assertFalse(small.truncated)


if __name__ == "__main__":
    unittest.main()
