"""SSE 响应层（对齐 EvoFlow ``app/gateway/routers/events.py`` 的订阅端点）。

原版对应：
    @router.get(...) subscribe_task_events   ← routers/events.py:173-178
    event_generator(thread_id)               ← :133

差异（台账已登记）：
    原版是 FastAPI 路由，挂在 gateway；本项目依赖里没有 fastapi/uvicorn，
    只有 starlette（LangGraph 自带），所以这里只做到"可挂载的 Starlette 响应"，
    不提供独立 HTTP 服务进程。
"""

from __future__ import annotations

from typing import Callable, Iterable

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.routing import Route

from ..events.sse import sse_event_stream

# 浏览器 EventSource 与代理都需要这几个头
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # 关掉 nginx 缓冲，否则事件会被攒着一起发
}


def build_sse_response(chunks: Iterable[str]) -> StreamingResponse:
    """把 SSE 文本块包装成 Starlette 流式响应。"""

    async def _body() -> Iterable[bytes]:
        for chunk in chunks:
            # 逐块立刻下发；缓冲会破坏"流式"观感
            yield chunk.encode("utf-8")

    return StreamingResponse(_body(), media_type="text/event-stream", headers=_SSE_HEADERS)


def create_sse_app(provider: Callable[[str], Iterable[dict]]) -> Starlette:
    """构造一个最小 SSE 应用。

    参数 ``provider(thread_id) -> Iterable[dict]`` 由调用方提供，
    通常就是 ``lambda tid: service.execute_stream(owner_id, tid, text)``。

    端点：``GET /runs/{thread_id}/events``，支持 ``Last-Event-ID`` 断线补发。
    """

    async def endpoint(request: Request) -> StreamingResponse:
        thread_id = request.path_params.get("thread_id", "")
        raw_last = request.headers.get("last-event-id", "0") or "0"
        try:
            last_id = int(raw_last)
        except ValueError:
            last_id = 0
        return build_sse_response(sse_event_stream(provider(thread_id), last_event_id=last_id))

    return Starlette(routes=[Route("/runs/{thread_id}/events", endpoint)])


__all__ = ["build_sse_response", "create_sse_app"]
