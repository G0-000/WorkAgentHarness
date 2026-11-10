"""章节测试共用装配：临时库 + fake 模型 + 真实 checkpointer + 真实工具目录。

原则：测试只用本项目真实入口（RunService / make_lead_agent / default_catalog），
不 mock 掉被测对象，避免"测了个假东西"。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from workagentharness.agents.checkpointer.provider import open_checkpointer
from workagentharness.agents.lead_agent.agent import make_lead_agent
from workagentharness.config.model_config import ChatModelConfig
from workagentharness.execution.run_service import RunService
from workagentharness.models.factory import create_chat_model
from workagentharness.persistence.db import open_database
from workagentharness.persistence.run_repository import RunRepository
from workagentharness.persistence.session_repository import SessionRepository
from workagentharness.tools.builtins import default_catalog

BACKEND_DIR = Path(__file__).resolve().parents[2]


class ServiceBundle:
    """一组可关闭的资源：业务库连接 + checkpoint 连接 + service。"""

    def __init__(self, *, with_tools: bool = True, middleware=None) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wah-ch-")
        self.db_path = str(Path(self._tmp.name) / "test.db")
        self.database = open_database(self.db_path)
        self.checkpoint_conn, self.saver = open_checkpointer(self.db_path)
        self.sessions = SessionRepository(self.database)
        self.runs = RunRepository(self.database)

        config = ChatModelConfig(provider="fake", model="tutorial-fake", temperature=0)
        self.model = create_chat_model(config)
        catalog = default_catalog()
        self.agent = make_lead_agent(
            self.model,
            tools=catalog.langchain_tools() if with_tools else [],
            middleware=list(middleware or []),
            checkpointer=self.saver,
        )
        self.service = RunService(self.agent, self.sessions, self.runs)

    def run_once(self, text: str, session_id: str = "s1") -> object:
        self.sessions.create(session_id, "local-user")
        return self.service.execute("local-user", session_id, text)

    def close(self) -> None:
        self.checkpoint_conn.close()
        self.database.close()
        self._tmp.cleanup()


def python_exe() -> str:
    """当前解释器（uv run 注入的同一个环境），供 CLI 子进程测试使用。"""
    return sys.executable


def cli_command(*args: str) -> list[str]:
    """真实的模块入口，而不是直接调用函数——验证 argparse 与装配层。"""
    return [python_exe(), "-m", "workagentharness.cli.main", *args]
