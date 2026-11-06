"""流式事件：把 Agent 图运行过程归一化成前端可消费的事件。

对应第三篇第 10 章（WAH-TOOL-006 流事件生产与消费、WAH-API-002 流式输出）。

为什么需要这一层：
    LangGraph 的原始 stream 输出是 {mode: chunk} 的混合流，
    前端不应该直接解析 LangGraph 内部结构（节点名、消息对象、metadata）。
    所以在应用层做一次"协议翻译"：LangGraph chunk → 稳定事件字典。

事件类型（当前最小集，只负责 Agent 图内部过程）：
    text_delta   {text}          模型输出的文本增量
    tool_call    {name, args}    模型发起一次工具调用
    tool_result  {name, ok}      工具执行完成（内容不直接下发，避免 UI 塞爆）

run_start / run_end 属于"运行生命周期"，由 RunService 产出（见 execution/run_service.py），
事件层不重复发送，避免一次运行出现两个结束事件。

后续可扩展（本篇先不做）：
    step_start / step_end（节点级）、resume、interrupt、usage。
"""

from __future__ import annotations

from typing import Any, Iterator

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

Event = dict[str, Any]


def _tool_result_ok(message: ToolMessage) -> bool:
    """判断工具结果是否成功：约定工具返回 "[ErrorCode] ..." 前缀视为失败。"""
    content = str(message.content or "")
    return not content.startswith("[")


def stream_agent_run(
    agent,
    input_messages: list[tuple[str, str]],
    *,
    thread_id: str,
) -> Iterator[Event]:
    """运行 Agent 并把过程翻译成事件流。

    参数：
        agent:           已构造的 Agent（带 checkpointer）
        input_messages:  形如 [("user", "你好")] 的输入
        thread_id:       会话 ID，同时作为 LangGraph checkpoint 的 thread

    产出：按发生顺序 yield text_delta / tool_call / tool_result 事件；
    调用方可以边收边渲染。运行开始与结束由 RunService 负责。
    """
    # stream_mode 同时订阅两类：messages（模型 token 流）、updates（节点状态变更）
    for mode, chunk in agent.stream(
        {"messages": input_messages},
        {"configurable": {"thread_id": thread_id}},
        stream_mode=["messages", "updates"],
    ):
        if mode == "messages":
            message_chunk, _metadata = chunk
            # 只关心模型输出的文本增量，工具结果走 updates 分支
            if isinstance(message_chunk, (AIMessage, AIMessageChunk)):
                text = message_chunk.content
                if isinstance(text, str) and text:
                    yield {"type": "text_delta", "text": text}
            continue

        if mode == "updates":
            # updates 的形状是 {节点名: {"messages": [新消息...]}}
            for _node, payload in (chunk or {}).items():
                for message in (payload or {}).get("messages", []):
                    if isinstance(message, AIMessage):
                        # 模型决定调用工具：每个 tool_call 产出一条事件
                        for call in message.tool_calls or []:
                            yield {
                                "type": "tool_call",
                                "name": call.get("name", ""),
                                "args": call.get("args", {}),
                            }
                    elif isinstance(message, ToolMessage):
                        yield {
                            "type": "tool_result",
                            "name": message.name or "",
                            "ok": _tool_result_ok(message),
                        }
