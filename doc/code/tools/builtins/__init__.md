# tools/builtins/__init__.py — 内置工具集合与默认目录

> **源码路径**: `backend/packages/harness/workagentharness/tools/builtins/__init__.py`
> **对应功能**: WAH-TOOL-003、WAH-TOOL-004

## 顺序执行链

```text
default_catalog()
  │
  ▼ 1. catalog = ToolCatalog()
  │
  ▼ 2. 逐项注册
  ├─ register(calculator,     tier="core",      aliases=("calc","math"))
  ├─ register(read_text_file, tier="workspace", aliases=("read_file",))
  └─ register(list_directory, tier="workspace", aliases=("ls",))
  │
  ▼ 3. 返回 catalog
  │
  ▼ 4. 调用方（cli/main.py）
  ├─ catalog.langchain_tools() → make_lead_agent(tools=...)
  ├─ catalog.describe_all()    → 日志 / UI（可选）
  └─ catalog.schemas()         → 排查"模型看到了什么工具"
```

## 为什么先只放两类工具

| 工具 | 为什么先做 | 风险 |
|---|---|---|
| `calculator` | 无副作用，最适合验证"模型 → 工具 → 结果回传"闭环 | 低（纯计算） |
| `read_text_file` / `list_directory` | 只读 + 边界校验，演示宿主边界且不引入写风险 | 低（只读） |

**来源标注**：这四个工具都是本项目自造，EvoFlow 无同名符号——算术走 `code_execution_tool.py`，文件能力拆在 `host_direct/read_file.py`、`list_dir.py` 等文件里。见 [台账 · 八](../../../dev/学习教程册/EvoFlow对照台账与差异建议.md)。

写文件、执行命令、浏览器控制属于高风险面，需要额外治理（审批、白名单、超时），本篇先不做。

## 新增工具步骤

1. 在本目录新增 `@tool` 函数（返回值用字符串，失败返回 `[ErrorCode] 原因`）
2. 在 `__all__` 与 `default_catalog()` 里注册，给别名和 tier
3. 在 `doc/code/tools/builtins/` 下补一份一文件一文档
4. 在 `doc/dev/学习教程册/三-.../` 对应小节记录验收

## 边界与待补

- 无写文件 / 编辑工具
- 无 shell / 终端工具
- 无搜索（网络搜索、文件全文搜索）
- 无 MCP 工具接入
