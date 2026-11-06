# tools/__init__.py — 工具层出口

> **源码路径**: `backend/packages/harness/workagentharness/tools/__init__.py`
> **对应功能**: WAH-TOOL-001、WAH-TOOL-002

## 顺序执行链

```text
外部 import workagentharness.tools
  │
  ▼ 1. 从 catalog.py 导出
  ├─ ToolCatalog    # 工具目录
  └─ ToolEntry      # 单条工具记录
  │
  ▼ 2. 从 result.py 导出
  ├─ ToolResult        # 结果结构
  ├─ shape_result      # 结果收敛函数
  ├─ truncate_text     # 截断工具
  └─ MAX_RESULT_CHARS  # 截断上限常量
  │
  ▼ 3. 使用方
  ├─ cli/main.py              → default_catalog().langchain_tools()
  ├─ execution/run_service.py → 间接消费工具结果
  └─ doc/code 文档             → 对照导出符号
```

## 关键设计

- **出口收敛**：上层只从 `tools` 包导入这三类东西，不直接 import 子模块内部实现，后续重构不影响调用方。
- **not 导出 builtins**：`builtins` 需要显式 `from workagentharness.tools.builtins import default_catalog`，避免 import 工具层时连带加载全部内置工具。

## 边界与待补

- 未导出 `ToolEntry.describe` 之外的观测接口
- 未提供按 tier 分组的便捷函数
