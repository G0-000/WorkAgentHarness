# tools/catalog.py — 工具目录

> **源码路径**: `backend/packages/harness/workagentharness/tools/catalog.py`
> **对应功能**: WAH-TOOL-001

## 顺序执行链

```text
default_catalog()                              # builtins/__init__.py
  │
  ▼ 1. catalog.register(tool, tier, aliases, source)
  ├─ 重名检查：tool.name 已存在 → ValueError（拒绝静默覆盖）
  ├─ 写 _entries[name] = ToolEntry(...)
  └─ 别名逐个写 _alias_index[alias] = name（冲突同样报错）
  │
  ▼ 2. catalog.langchain_tools() → [BaseTool, ...]
  └─ 传给 make_lead_agent(tools=...) → create_agent 编译工具节点
  │
  ▼ 3. 运行时解析（可选）
  ├─ resolve("calc")  → ToolEntry("calculator")
  ├─ resolve("未知")   → None（不抛异常，调用方决定如何处理）
  └─ get("calculator") → 找不到抛 KeyError（装配期宁可早失败）
  │
  ▼ 4. 观测
  ├─ describe_all() → [{name, tier, source, aliases, description}]
  └─ schemas()      → [{name, description, args(JSON Schema)}]
```

## ToolCatalog 方法

| 方法 | 作用 | 失败行为 |
|---|---|---|
| `register` | 注册工具 + 别名 | 重名/别名冲突 → `ValueError` |
| `resolve` | 按名或别名查 | 找不到 → `None` |
| `get` | 按名取 | 找不到 → `KeyError` |
| `names` | 全部正式名 | — |
| `describe_all` | UI/日志元数据 | — |
| `schemas` | 模型侧 schema | — |
| `langchain_tools` | 交给 create_agent | — |

## 关键设计

1. **两层视图**：模型只看 `schemas()`；UI/日志看 `describe_all()`（多出 tier、来源、别名）。
2. **别名唯一**：一个别名只能指向一个工具，冲突直接报错，避免"模型调 calc 结果跑到 math 工具"。
3. **注册顺序稳定**：`langchain_tools()` 按注册顺序返回，保证多次运行的 schema 顺序一致（便于对比 diff）。

## 边界与待补

- 无 tier 分层过滤（EvoFlow 有 runtime/core/workspace/plan/goal/optional/retired 七档）
- 无按 Agent / session 白名单过滤
- 无 MCP / host_direct / zcode_port 等外部来源
- 无工具启停开关与退役标记
