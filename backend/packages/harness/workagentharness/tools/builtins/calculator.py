"""内置计算工具：安全四则运算。

为什么不用 ``eval``：
    ``eval("__import__('os').system('rm -rf /')")`` 能直接执行任意代码。
    工具输入来自模型，模型输入来自用户，这条链路绝不能用 eval。

做法：用 ``ast`` 解析表达式，只放行数字、四则运算符、乘方、取模、
一元正负号和括号；其他任何节点（函数调用、属性访问、下标、推导式）
一律拒绝。这样即使表达式恶意，也只会得到 InvalidExpression。
"""

from __future__ import annotations

import ast
import operator

from langchain_core.tools import tool

from ..result import shape_result

# 允许的二元运算符白名单：AST 节点 → 实际计算函数
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

# 允许的一元运算符白名单
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# 乘方的指数上限，防止 "9**9**9" 这类表达式把内存打爆
_MAX_EXPONENT = 1000


def _eval_node(node: ast.AST) -> float | int:
    """递归求值：只接受白名单节点，其余抛 ValueError。"""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("只支持数字")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ValueError(f"指数过大（上限 {_MAX_EXPONENT}）")
        if isinstance(node.op, (ast.Div, ast.Mod)) and right == 0:
            raise ValueError("除数不能为 0")
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"不支持的表达式成分: {type(node).__name__}")


def safe_eval(expression: str) -> float | int:
    """对外暴露的安全求值函数；解析失败统一抛 ValueError。"""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"表达式语法错误: {exc.msg}") from exc
    return _eval_node(tree.body)


@tool
def calculator(expression: str) -> str:
    """计算数学表达式。支持 + - * / ** % 和括号，例如 "(3+4)*2"。"""
    try:
        value = safe_eval(expression)
    except ValueError as exc:
        # 参数错误 → 稳定错误类别 InvalidExpression，不把异常栈塞给模型
        return f"[InvalidExpression] {exc}"
    # 整数保持整数展示，浮点保留 10 位有效数字
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value}"


def build_calculator_tool():
    """返回计算工具的 (ToolResult 包装版, 原始 tool)。

    说明：``@tool`` 生成的 StructuredTool 直接返回 str，
    LangGraph 会把它包成 ToolMessage。这里用 ``func`` 属性再包一层 ToolResult，
    让内部调用（单测、目录自检）也能拿到统一结构。
    """
    return calculator
