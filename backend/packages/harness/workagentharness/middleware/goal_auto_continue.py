"""自动续跑中间件（对齐 EvoFlow ``agents/goal/goal_auto_continue_middleware.py``）。

原版对应：
    class GoalAutoContinueMiddleware        ← goal_auto_continue_middleware.py:120
    def after_model / aafter_model          ← :125 起
    机制：@hook_config(can_jump_to=["model","end"]) → 返回 {"jump_to": "model"} 回到模型节点

差异（台账已登记）：
    原版只在 goal 模式下启用，靠 goal 行记录判断"目标是否完成"；
    学习版没有 goal 模块，用"最后一条 AI 消息是否标记未完成"这个简化判据，
    并固定 MAX_STEPS＝8（原版由 goal 配置决定，不是常量）。
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import AIMessage, HumanMessage

# 一次运行内最多自动续跑几轮，防止"一直续跑烧 token"（原版注释里同样有此担心）
MAX_STEPS = 8

# 续跑计数按 thread 存。
# 为什么不用 ContextVar：LangGraph 每跳一个节点都会新建执行上下文，
# ContextVar 的写入在跨节点时不保留，实测会导致计数永远为 0 → 无限续跑。
# 原版把步数记在 goal 行（数据库）里，这里退一步用进程内 dict，差异见台账。
_STEPS: dict[str, int] = {}


def _thread_key(runtime: Any) -> str:
    """从 runtime 取 thread_id 作为计数键；取不到就退回全局键。"""
    context = getattr(runtime, "context", None) if runtime is not None else None
    try:
        thread_id = str(context.get("thread_id") or "").strip() if context else ""
    except AttributeError:
        thread_id = ""
    return thread_id or "__default__"

# 判定"这一轮没做完"的标记：只认明确的未完成信号。
# 注意不要放"继续""接着"——用户输入里出现这两个词时，模型回显也会带上，
# 会被误判成永远未完成，进而无限续跑（实测会撞 GraphRecursionError）。
_UNFINISHED_MARKERS = ("TODO", "待办", "尚未完成", "下一步")
# 内容为空（纯工具调用轮）也视为未完成
_EMPTY_CONTENT_MAX = 0


def _last_ai(messages: list[Any]) -> AIMessage | None:
    """取最后一条 AIMessage（原版 :79 ``_last_ai``）。"""
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def _is_unfinished(message: AIMessage | None) -> bool:
    """判断模型这一轮是否"话没说完"。"""
    if message is None:
        return False
    # 还有未执行的工具调用 → 肯定没做完
    if getattr(message, "tool_calls", None):
        return True
    content = str(message.content or "").strip()
    if len(content) <= _EMPTY_CONTENT_MAX:
        return True
    return any(marker in content for marker in _UNFINISHED_MARKERS)


def reset_step_count(thread_id: str = "") -> None:
    """清掉某个 thread（或全部）的续跑计数（由调用方在新 run 开始时调用）。"""
    if thread_id:
        _STEPS.pop(thread_id, None)
    else:
        _STEPS.clear()


def current_step_count(thread_id: str = "") -> int:
    """当前 thread 已经自动续跑了几轮。"""
    return _STEPS.get(thread_id or "__default__", 0)


class GoalAutoContinueMiddleware(AgentMiddleware):
    """模型一轮说完但事情没做完时，自动回到模型节点再跑一轮。"""

    @hook_config(can_jump_to=["model", "end"])
    def after_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        key = _thread_key(runtime)
        steps = _STEPS.get(key, 0)

        messages = list(state.get("messages", []) if isinstance(state, dict) else [])
        # 到达上限、或这一轮已经做完 → 停在 end，同时清掉计数
        if steps >= MAX_STEPS or not _is_unfinished(_last_ai(messages)):
            _STEPS.pop(key, None)
            return {"jump_to": "end"}

        _STEPS[key] = steps + 1
        # 塞一条"继续"的用户消息，同时声明跳回 model 节点
        return {
            "jump_to": "model",
            "messages": [HumanMessage(content="继续完成未完成的步骤。", name="auto_continue")],
        }


__all__ = [
    "GoalAutoContinueMiddleware",
    "MAX_STEPS",
    "reset_step_count",
    "current_step_count",
]
