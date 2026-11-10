"""第 12 章验收：事件结构、SSE 编码、缓冲补发与 CLI 消费（WAH-TOOL-006、API-002、UI-002/004）。

对应教程：12. 事件SSE恢复和界面消费。
"""

from __future__ import annotations

import unittest

from tests.chapters.helpers import ServiceBundle
from workagentharness.events.sse import (
    HEARTBEAT_SECONDS, EventBuffer, decode_sse_payload, encode_sse_event,
    heartbeat_comment, sse_event_stream,
)


class SseCodecTest(unittest.TestCase):
    def test_encode_format(self):
        text = encode_sse_event({"type": "text_delta", "text": "你好"}, event_id=1)
        self.assertTrue(text.startswith("id: 1\nevent: text_delta\ndata: "))
        self.assertTrue(text.endswith("\n\n"))
        self.assertEqual(decode_sse_payload(text)["text"], "你好")

    def test_multiline_payload(self):
        # JSON 会把换行转义成 \n，所以实际只有一行 data；换行还原由 json 解码负责
        text = encode_sse_event({"type": "x", "text": "a\nb"}, event_id=2)
        self.assertEqual(text.count("data: "), 1)
        self.assertEqual(decode_sse_payload(text)["text"], "a\nb")

    def test_decode_garbage_returns_none(self):
        self.assertIsNone(decode_sse_payload("event: x\n"))
        self.assertIsNone(decode_sse_payload("data: {bad}\n\n"))

    def test_heartbeat_constants(self):
        self.assertEqual(HEARTBEAT_SECONDS, 15)
        self.assertEqual(heartbeat_comment(), ": ping\n\n")


class EventBufferTest(unittest.TestCase):
    def test_capacity_is_200_and_since(self):
        buffer = EventBuffer()
        self.assertEqual(buffer._items.maxlen, 200)
        ids = [buffer.append({"type": "t", "i": i})[0] for i in range(3)]
        self.assertEqual(ids, [1, 2, 3])
        self.assertEqual(len(buffer.since(1)), 2)
        self.assertEqual(buffer.since(3), [])

    def test_old_events_evicted(self):
        buffer = EventBuffer(maxlen=2)
        for i in range(3):
            buffer.append({"type": "t", "i": i})
        self.assertEqual(len(buffer.since(0)), 2)

    def test_stream_injects_heartbeat(self):
        buffer = EventBuffer()
        frames = list(sse_event_stream(
            [{"type": "a"}, {"type": "b"}], buffer=buffer, heartbeat_every=2
        ))
        self.assertEqual(len(frames), 3)
        self.assertEqual(frames[-1], ": ping\n\n")


class RunStreamTest(unittest.TestCase):
    def setUp(self):
        self.bundle = ServiceBundle(with_tools=True)

    def tearDown(self):
        self.bundle.close()

    def test_event_sequence_without_tools(self):
        self.bundle.sessions.create("s1", "local-user")
        events = list(self.bundle.service.execute_stream("local-user", "s1", "你好"))
        self.assertEqual(events[0]["type"], "run_start")
        self.assertEqual(events[-1]["type"], "run_end")
        self.assertEqual(events[-1]["status"], "completed")
        self.assertTrue(any(e["type"] == "text_delta" for e in events))

    def test_tool_call_and_result_events(self):
        self.bundle.sessions.create("s1", "local-user")
        events = list(self.bundle.service.execute_stream("local-user", "s1", "计算 1+2"))
        types = [e["type"] for e in events]
        self.assertIn("tool_call", types)
        self.assertIn("tool_result", types)
        tool_result = next(e for e in events if e["type"] == "tool_result")
        self.assertTrue(tool_result["ok"])
        self.assertEqual(events[-1]["status"], "completed")

    def test_sse_three_frames(self):
        self.bundle.sessions.create("s1", "local-user")
        frames = list(sse_event_stream(
            self.bundle.service.execute_stream("local-user", "s1", "你好"), buffer=EventBuffer()
        ))
        ids = [line for frame in frames for line in frame.splitlines() if line.startswith("id: ")]
        self.assertEqual(ids, ["id: 1", "id: 2", "id: 3"])


if __name__ == "__main__":
    unittest.main()
