"""事件层对外出口。

对应第三篇第 10 章：事件生产（WAH-TOOL-006）与流式输出（WAH-API-002）。
SSE 传输、断线恢复、前端消费（WAH-UI-002/004）留到同章后续小节。
"""

from .stream import Event, stream_agent_run

__all__ = ["Event", "stream_agent_run"]
