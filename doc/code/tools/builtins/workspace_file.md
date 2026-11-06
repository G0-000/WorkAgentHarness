# tools/builtins/workspace_file.py — 只读文件工具与宿主边界

> **源码路径**: `backend/packages/harness/workagentharness/tools/builtins/workspace_file.py`
> **对应功能**: WAH-TOOL-003（文件/终端/宿主边界）

## 顺序执行链

```text
模型发起 tool_call: read_text_file(path="backend/config.yaml")
  │
  ▼ 1. resolve_in_workspace(path)
  ├─ 空路径                     → ValueError("路径不能为空")
  ├─ 绝对路径（/etc/passwd）    → ValueError("不允许绝对路径")
  ├─ root = WORKAGENT_WORKSPACE 或 cwd
  ├─ target = (root / path).resolve()
  └─ target 不在 root 下        → ValueError("路径越出工作区范围")
  │
  ▼ 2. 文件检查
  ├─ 不存在 → "[NotFound]"
  ├─ 不是文件 → "[NotAFile]"
  ├─ 读失败（OSError） → "[ReadError] 异常类型名"
  └─ 非 UTF-8（二进制） → "[NotText]"
  │
  ▼ 3. shape_result(...) 截断到 8000 字符
  │
  ▼ 4. 返回文本给模型
```

## 边界规则

| 规则 | 拦住的攻击 | 实现位置 |
|---|---|---|
| 拒绝绝对路径 | `/etc/passwd`、`~/.ssh/id_rsa` | `resolve_in_workspace` |
| 拒绝 `..` 逃逸 | `../../../etc/passwd` | `resolve()` 后判断 root 前缀 |
| 拒绝符号链接逃逸 | 工作区内指向外部的软链 | 同上（`resolve()` 会展开软链） |
| 只读 | 模型删/改用户文件 | 本模块无写方法 |

## 关键设计

1. **边界在代码里，不在提示词里**：不能靠"请只读工作区文件"的提示约束模型；`resolve_in_workspace` 是硬校验。
2. **错误带类别**：`[PathNotAllowed]` / `[NotFound]` / `[NotText]`，模型可以据此改路径或放弃，而不是拿到 Python 异常。
3. **工作区根可配**：`WORKAGENT_WORKSPACE` 环境变量，缺省当前进程工作目录；部署时改成业务数据目录。

## 边界与待补

- 无写文件、无编辑、无批量搜索（`grep`/`glob`）
- 无终端命令执行（shell 属 WAH-TOOL-010，需命令白名单 + 超时 + 输出上限 + 审批）
- 无文件大小上限预检（先读进内存再截断，超大文件仍会占内存）
- 无符号链接告警（越界被拒，但不向调用方说明原因）
