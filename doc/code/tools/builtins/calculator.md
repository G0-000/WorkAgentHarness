# tools/builtins/calculator.py — 安全计算工具

> **源码路径**: `backend/packages/harness/workagentharness/tools/builtins/calculator.py`
> **对应功能**: WAH-TOOL-003（内置工具最小实现）

## 顺序执行链

```text
模型发起 tool_call: calculator(expression="(3+4)*2")
  │
  ▼ 1. LangGraph 工具节点执行 @tool 函数
  │
  ▼ 2. safe_eval("(3+4)*2")
  ├─ ast.parse(expression, mode="eval")
  │    └─ SyntaxError → ValueError("表达式语法错误")
  └─ _eval_node(tree.body) 递归求值
       ├─ ast.Constant(int/float)             → 直接返回（bool 拒绝）
       ├─ ast.BinOp(Add/Sub/Mult/Div/Pow/Mod) → 白名单运算符计算
       │    ├─ Pow 指数 > 1000               → ValueError("指数过大")
       │    └─ Div/Mod 除数为 0               → ValueError("除数不能为 0")
       ├─ ast.UnaryOp(UAdd/USub)              → 一元正负
       └─ 其他节点（Call/Attribute/Subscript/ListComp…）→ ValueError
  │
  ▼ 3. 结果整形
  ├─ 浮点且是整数 → 转 int 展示
  └─ 返回字符串 "14"
  │
  ▼ 4. LangGraph 包成 ToolMessage 回给模型
```

## 为什么不直接 eval

| 输入 | `eval` 结果 | 本实现 |
|---|---|---|
| `1+1` | 2 | 2 |
| `__import__('os').system('rm -rf ~')` | **执行命令** | `[InvalidExpression] 不支持的表达式成分: Call` |
| `open('/etc/passwd').read()` | **读文件** | 拒绝 |
| `9**9**9` | 卡死/内存爆 | 指数上限 1000，拒绝 |

## 关键设计

1. **AST 白名单**：只放行字面量、四则运算、乘方、取模、一元正负；`Call` / `Attribute` / `Subscript` 一律拒绝。
2. **爆炸防护**：指数上限 + 除零检查，避免一次工具调用打挂进程。
3. **错误可读**：失败返回 `[InvalidExpression] 原因`，模型能读懂并换一种表达重试，而不是拿到异常栈。

## 边界与待补

- 无科学计算（sin/cos/log/sqrt）、无变量、无单位
- 无大数精度控制（依赖 Python float 精度）
- 无计算步数/时间上限（超长表达式可能慢）
- 返回值没有走 `shape_result`（字符串结果由工具层统一处理）
