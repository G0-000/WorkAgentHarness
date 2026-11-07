"""SSE 编码与断线补发（对齐 EvoFlow ``app/gateway/agui_stream_encode.py`` + ``routers/events.py``）。

原版对应：
    encode_agui_event       ← app/gateway/agui_stream_encode.py:10
    decode_agui_payload     ← :19
    _enqueue_sse            ← app/gateway/routers/events.py:50
    event_generator         ← :133
    emit_task_heartbeat     ← :221

差异（台账已登记）：
    原版编码成 AG-UI 协议字节流；本项目事件是自定义 dict，编码成标准 SSE 文本，
    因此函数名为 ``encode_sse_event`` / ``decode_sse_payload``，不叫 agui。

SSE 三条硬规则（实现里逐条对应）：
    1. 每条事件以空行结束 —— 少一个空行，前端会把两条粘成一条。
    2. 多行数据拆成多行 ``data:`` —— 前端会自动拼回。
    3. 行分隔统一 ``\\n`` —— 不混用 ``\\r\\n``。
"""

from __future__ import annotations

import json
from collections import deque
from typing import Iterable, Iterator

# 心跳间隔（秒）：防止中间代理把长连接判为空闲断开（原版 emit_task_heartbeat 的作用）
HEARTBEAT_SECONDS = 15


def encode_sse_event(event: dict, *, event_id: int) -> str:
    """把一条事件编码成 SSE 文本（原版 encode_agui_event 的 SSE 版）。"""
    event_type = str(event.get("type") or "message")
    payload = json.dumps(event, ensure_ascii=False)

    lines = [f"id: {event_id}", f"event: {event_type}"]
    # 规则 2：多行数据要逐行加 data: 前缀，前端会拼回成一条
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    # 规则 1 + 3：以空行结束，全部用 \n
    return "\n".join(lines) + "\n\n"


def decode_sse_payload(raw: str) -> dict | None:
    """解析一段 SSE 文本为事件 dict（原版 decode_agui_payload 的 SSE 版）。"""
    data_lines: list[str] = []
    for line in (raw or "").splitlines():
        if line.startswith("data:"):
            data_lines.append(line[len("data:") :].lstrip())
    if not data_lines:
        return None
    try:
        return json.loads("\n".join(data_lines))
    except json.JSONDecodeError:
        return None


def heartbeat_comment() -> str:
    """心跳写成注释行（以 ``:`` 开头，客户端会忽略内容但保活连接）。"""
    return ": ping\n\n"


class EventBuffer:
    """最近若干条事件的内存缓冲，用于断线后按 Last-Event-ID 补发。

    原版把事件放 asyncio.Queue 推给订阅者；补发靠数据库或内存。
    学习版用定长 deque：够验证"补发不重不漏"，重启即丢（与注册表同理）。
    """

    def __init__(self, maxlen: int = 200) -> None:
        self._items: deque[tuple[int, str]] = deque(maxlen=maxlen)
        self._next_id = 1

    @property
    def next_id(self) -> int:
        return self._next_id

    def append(self, event: dict) -> tuple[int, str]:
        """登记一条事件，返回 (id, 编码后的文本)。"""
        event_id = self._next_id
        self._next_id += 1
        text = encode_sse_event(event, event_id=event_id)
        self._items.append((event_id, text))
        return event_id, text

    def since(self, last_event_id: int) -> list[str]:
        """返回 id > last_event_id 的事件文本（断线补发）。"""
        return [text for event_id, text in self._items if event_id > last_event_id]


def sse_event_stream(
    events: Iterable[dict],
    *,
    buffer: EventBuffer | None = None,
    last_event_id: int = 0,
    heartbeat_every: int = 0,
) -> Iterator[str]:
    """把事件序列编码成 SSE 文本流（原版 event_generator 的同步版）。

    参数：
        events:          产生事件的可迭代对象（通常是 service.execute_stream）
        buffer:          可选事件缓冲；传入时先补发 last_event_id 之后的事件
        last_event_id:   客户端上次收到的事件 id（断线重连时带上来）
        heartbeat_every: 每 N 条事件插一次心跳，0 表示不插
    """
    own_buffer = buffer or EventBuffer()

    # 断线重连：先把缺的部分补齐，再继续推新事件
    for text in own_buffer.since(last_event_id):
        yield text

    for index, event in enumerate(events, start=1):
        _event_id, text = own_buffer.append(event)
        yield text
        if heartbeat_every and index % heartbeat_every == 0:
            yield heartbeat_comment()


__all__ = [
    "encode_sse_event",
    "decode_sse_payload",
    "heartbeat_comment",
    "EventBuffer",
    "sse_event_stream",
    "HEARTBEAT_SECONDS",
]
