"""第 3 章验收：配置读取、字段校验与 provider 选择（WAH-RUN-001/002）。

对应教程：3. 配置模型供应商与凭证。
每条用例断言的是"报错原文"，不是"抛了个异常"——文档写了什么就必须报什么。
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from workagentharness.config.loader import load_chat_model_config
from workagentharness.config.model_config import ChatModelConfig
from workagentharness.models.factory import FakeChatModel, create_chat_model


class ConfigTest(unittest.TestCase):
    def _write(self, text: str) -> str:
        handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
        handle.write(text)
        handle.close()
        return handle.name

    def test_fake_config_loads(self):
        path = self._write("models:\n  chat:\n    provider: fake\n    model: tutorial-fake\n")
        config = load_chat_model_config(path)
        self.assertIsInstance(config, ChatModelConfig)
        self.assertEqual(config.provider, "fake")

    def test_missing_model_field(self):
        path = self._write("models:\n  chat:\n    provider: fake\n")
        with self.assertRaises(ValueError) as ctx:
            load_chat_model_config(path)
        self.assertIn("models.chat 配置字段无效", str(ctx.exception))

    def test_openai_compatible_requires_api_key(self):
        path = self._write("models:\n  chat:\n    provider: openai-compatible\n    model: m\n")
        with self.assertRaises(ValueError) as ctx:
            load_chat_model_config(path)
        self.assertEqual(str(ctx.exception), "openai-compatible provider 需要 api_key")

    def test_temperature_out_of_range(self):
        path = self._write(
            "models:\n  chat:\n    provider: fake\n    model: m\n    temperature: 3\n"
        )
        with self.assertRaises(ValueError) as ctx:
            load_chat_model_config(path)
        self.assertEqual(str(ctx.exception), "models.chat.temperature 必须在 0 到 2 之间")

    def test_env_variable_expansion(self):
        path = self._write(
            "models:\n  chat:\n    provider: fake\n    model: m\n    api_key: ${WAH_TEST_KEY}\n"
        )
        os.environ.pop("WAH_TEST_KEY", None)
        with self.assertRaises(ValueError) as ctx:
            load_chat_model_config(path)
        self.assertEqual(str(ctx.exception), "缺少必需的环境变量: WAH_TEST_KEY")

    def test_unknown_provider_rejected_at_factory(self):
        # 配置层不校验 provider 是否存在；工厂层才拒绝——两段职责必须在测试里分开
        path = self._write("models:\n  chat:\n    provider: nope\n    model: m\n")
        config = load_chat_model_config(path)  # 这一层通过
        with self.assertRaises(ValueError) as ctx:
            create_chat_model(config)
        self.assertEqual(str(ctx.exception), "不支持的模型 provider: nope")

    def test_factory_returns_fake_model(self):
        config = ChatModelConfig(provider="fake", model="tutorial-fake", temperature=0)
        self.assertIsInstance(create_chat_model(config), FakeChatModel)


if __name__ == "__main__":
    unittest.main()
