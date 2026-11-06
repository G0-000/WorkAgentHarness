"""工具目录：注册、别名解析、Schema 输出与 Agent 侧装配。

对应 EvoFlow 的 ``tools/tool_catalog.py`` 简化版。EvoFlow 有 tier 分层
（runtime / core / workspace / plan / goal / optional / retired），
学习版先只保留"注册 + 别名 + 查询 + 交给 Agent"四件事。

设计要点：
    1. 工具一律用 LangChain 的 ``@tool`` 装饰器定义（StructuredTool），
       自带 name / description / args_schema，可直接交给 ``create_agent``。
    2. 目录负责把"给模型看的工具"和"UI/日志看的元数据"分开：
       模型只看 schema；UI 额外知道来源 tier 和别名。
    3. 别名允许一个工具被多个名字触发（如 ``calc`` → ``calculator``），
       但最终解析成同一个实现，避免 fork 出两份逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.tools import BaseTool


@dataclass(frozen=True)
class ToolEntry:
    """工具目录中的一条记录。"""

    tool: BaseTool
    tier: str = "core"                      # 学习版先固定 core；对齐 EvoFlow 的分层留待扩展
    aliases: tuple[str, ...] = ()           # 备选名字，如 ("calc",)
    source: str = "builtin"                 # 来源：builtin / mcp / host / ...

    @property
    def name(self) -> str:
        return self.tool.name

    def describe(self) -> dict[str, Any]:
        """给 UI / 日志 / 调试用的元数据（不含可执行对象）。"""
        return {
            "name": self.name,
            "tier": self.tier,
            "source": self.source,
            "aliases": list(self.aliases),
            "description": (self.tool.description or "").strip(),
        }


@dataclass
class ToolCatalog:
    """工具注册表。

    用法：
        catalog = ToolCatalog()
        catalog.register(calculator, aliases=("calc",))
        tools = catalog.langchain_tools()      # 交给 make_lead_agent
    """

    _entries: dict[str, ToolEntry] = field(default_factory=dict)
    _alias_index: dict[str, str] = field(default_factory=dict)

    def register(
        self,
        tool: BaseTool,
        *,
        tier: str = "core",
        aliases: tuple[str, ...] = (),
        source: str = "builtin",
    ) -> ToolEntry:
        """注册一个工具；重名直接报错，避免静默覆盖。"""
        name = tool.name
        if name in self._entries:
            raise ValueError(f"工具已存在，拒绝重复注册: {name}")
        entry = ToolEntry(tool=tool, tier=tier, aliases=aliases, source=source)
        self._entries[name] = entry
        for alias in aliases:
            if alias in self._alias_index:
                raise ValueError(f"别名冲突: {alias}")
            self._alias_index[alias] = name
        return entry

    def resolve(self, name_or_alias: str) -> ToolEntry | None:
        """按正式名或别名解析工具；找不到返回 None（不抛异常，便于调用方决定）。"""
        key = name_or_alias.strip()
        if key in self._entries:
            return self._entries[key]
        canonical = self._alias_index.get(key)
        return self._entries.get(canonical) if canonical else None

    def get(self, name: str) -> ToolEntry:
        """按名字取工具，找不到抛 KeyError（内部装配用，宁可早失败）。"""
        entry = self.resolve(name)
        if entry is None:
            raise KeyError(f"未知工具: {name}")
        return entry

    def names(self) -> list[str]:
        return sorted(self._entries)

    def describe_all(self) -> list[dict[str, Any]]:
        """返回全部工具的元数据快照（UI / 日志 / 文档用）。"""
        return [entry.describe() for entry in self._entries.values()]

    def schemas(self) -> list[dict[str, Any]]:
        """返回模型侧 schema（name / description / args），用于排查"模型看到了什么"。"""
        result = []
        for entry in self._entries.values():
            result.append({
                "name": entry.name,
                "description": (entry.tool.description or "").strip(),
                "args": entry.tool.args_schema.model_json_schema()
                if entry.tool.args_schema else {},
            })
        return result

    def langchain_tools(self) -> list[BaseTool]:
        """交给 ``create_agent`` 的工具列表（顺序按注册顺序，保持稳定）。"""
        return [entry.tool for entry in self._entries.values()]
