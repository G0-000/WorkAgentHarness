"""最小 Middleware：工具调用审计。

对应第三篇第 9 章的 WAH-TOOL-005（Middleware 调用链）最小实现。

Middleware 的位置：
    ``create_agent(model, tools, middleware=[...])`` 里传进去的中间件，
    会在图运行的固定节点前后被调用。本类只挂 ``wrap_tool_call``：
    工具真正执行之前记一次开始，执行之后记工具名、耗时、结果长度、
    是否报错。它是"工具活动"能被 UI 展示（WAH-UI-004）的数据来源。

为什么用 middleware 而不是在工具函数里写日志：
    日志是横切关注点。写进每个工具会让工具函数变成"业务 + 日志"混合体，
    将来换日志格式要改所有工具。middleware 只写一次，所有工具自动生效。
"""

from __future__ import annotations

import logging
import time

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

# 用标准 logging，交给入口层决定输出到终端还是文件
logger = logging.getLogger("workagent.tools")


class ToolAuditMiddleware(AgentMiddleware):
    """工具调用前后打点，记录耗时与结果规模。

    注意：``name`` 是 AgentMiddleware 的只读属性，不要自己赋值。
    """

    def __init__(self) -> None:
        super().__init__()

    def wrap_tool_call(self, request, handler):
        """包住一次工具调用。

        参数：
            request: ToolCallRequest，含 tool_call（name / args / id）
            handler: 真正执行工具的下一层（可能是别的 middleware 或工具本身）

        约定：这里不吞异常。工具抛错时让异常继续向上走，
        由 RunService 统一转成 failed 终态——middleware 只观测，不改语义。
        """
        tool_call = getattr(request, "tool_call", {}) or {}
        tool_name = tool_call.get("name", "unknown")
        started = time.perf_counter()
        logger.info("tool.start name=%s", tool_name)
        try:
            result = handler(request)
        except Exception as exc:
            # 只记异常类型名，不记原文（可能含用户输入）
            elapsed = (time.perf_counter() - started) * 1000
            logger.warning(
                "tool.fail name=%s elapsed_ms=%.1f error=%s",
                tool_name, elapsed, type(exc).__name__,
            )
            raise
        elapsed = (time.perf_counter() - started) * 1000
        # ToolMessage 才有 content；其他类型（如 Command）只记类型
        if isinstance(result, ToolMessage):
            logger.info(
                "tool.end name=%s elapsed_ms=%.1f content_chars=%d",
                tool_name, elapsed, len(str(result.content)),
            )
        else:
            logger.info(
                "tool.end name=%s elapsed_ms=%.1f result_type=%s",
                tool_name, elapsed, type(result).__name__,
            )
        return result
