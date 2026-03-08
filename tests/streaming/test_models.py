"""Tests for streaming data models."""

from __future__ import annotations

from unifiedui_sdk.streaming.models import StreamMessage, StreamMessageType


class TestStreamMessageType:
    """Tests for StreamMessageType enum."""

    def test_core_events_present(self) -> None:
        core = {
            "STREAM_START",
            "TEXT_STREAM",
            "STREAM_NEW_MESSAGE",
            "STREAM_END",
            "MESSAGE_COMPLETE",
            "TITLE_GENERATION",
            "ERROR",
        }
        values = {t.value for t in StreamMessageType}
        assert core.issubset(values)

    def test_reasoning_events_present(self) -> None:
        reasoning = {"REASONING_START", "REASONING_STREAM", "REASONING_END"}
        values = {t.value for t in StreamMessageType}
        assert reasoning.issubset(values)

    def test_tool_call_events_present(self) -> None:
        tool = {"TOOL_CALL_START", "TOOL_CALL_STREAM", "TOOL_CALL_END"}
        values = {t.value for t in StreamMessageType}
        assert tool.issubset(values)

    def test_multi_agent_events_present(self) -> None:
        multi_agent = {
            "PLAN_START",
            "PLAN_STREAM",
            "PLAN_COMPLETE",
            "SUB_AGENT_START",
            "SUB_AGENT_STREAM",
            "SUB_AGENT_END",
            "SYNTHESIS_START",
            "SYNTHESIS_STREAM",
        }
        values = {t.value for t in StreamMessageType}
        assert multi_agent.issubset(values)

    def test_trace_event_present(self) -> None:
        assert StreamMessageType.TRACE == "TRACE"

    def test_total_count(self) -> None:
        assert len(StreamMessageType) == 22

    def test_string_comparison(self) -> None:
        assert StreamMessageType.TEXT_STREAM == "TEXT_STREAM"
        assert StreamMessageType.ERROR == "ERROR"


class TestStreamMessage:
    """Tests for StreamMessage model."""

    def test_defaults(self) -> None:
        msg = StreamMessage(type=StreamMessageType.TEXT_STREAM)
        assert msg.type == StreamMessageType.TEXT_STREAM
        assert msg.content == ""
        assert msg.config == {}

    def test_with_content(self) -> None:
        msg = StreamMessage(type=StreamMessageType.TEXT_STREAM, content="hello")
        assert msg.content == "hello"

    def test_with_config(self) -> None:
        msg = StreamMessage(
            type=StreamMessageType.TOOL_CALL_START,
            config={"tool_name": "search", "tool_arguments": {"q": "test"}},
        )
        assert msg.config["tool_name"] == "search"
        assert msg.config["tool_arguments"]["q"] == "test"

    def test_model_dump(self) -> None:
        msg = StreamMessage(
            type=StreamMessageType.ERROR,
            content="something went wrong",
            config={"code": 500},
        )
        dumped = msg.model_dump()
        assert dumped["type"] == "ERROR"
        assert dumped["content"] == "something went wrong"
        assert dumped["config"]["code"] == 500

    def test_model_dump_json(self) -> None:
        msg = StreamMessage(type=StreamMessageType.STREAM_START)
        json_str = msg.model_dump_json()
        assert '"STREAM_START"' in json_str

    def test_all_types_constructible(self) -> None:
        for msg_type in StreamMessageType:
            msg = StreamMessage(type=msg_type)
            assert msg.type == msg_type
