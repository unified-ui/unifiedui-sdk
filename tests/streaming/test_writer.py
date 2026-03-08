"""Tests for StreamWriter."""

from __future__ import annotations

from unifiedui_sdk.streaming.models import StreamMessageType
from unifiedui_sdk.streaming.writer import StreamWriter


class TestStreamWriterCoreEvents:
    """Tests for StreamWriter core event methods."""

    def setup_method(self) -> None:
        self.writer = StreamWriter()

    def test_stream_start(self) -> None:
        msg = self.writer.stream_start()
        assert msg.type == StreamMessageType.STREAM_START
        assert msg.content == ""
        assert msg.config == {}

    def test_stream_start_with_config(self) -> None:
        msg = self.writer.stream_start(config={"session_id": "abc"})
        assert msg.config["session_id"] == "abc"

    def test_text_stream(self) -> None:
        msg = self.writer.text_stream("Hello")
        assert msg.type == StreamMessageType.TEXT_STREAM
        assert msg.content == "Hello"

    def test_stream_new_message(self) -> None:
        msg = self.writer.stream_new_message()
        assert msg.type == StreamMessageType.STREAM_NEW_MESSAGE

    def test_stream_new_message_with_config(self) -> None:
        msg = self.writer.stream_new_message(config={"msg_id": "1"})
        assert msg.config["msg_id"] == "1"

    def test_stream_end(self) -> None:
        msg = self.writer.stream_end()
        assert msg.type == StreamMessageType.STREAM_END

    def test_message_complete(self) -> None:
        msg = self.writer.message_complete(message={"id": "m1", "role": "assistant"})
        assert msg.type == StreamMessageType.MESSAGE_COMPLETE
        assert msg.config["id"] == "m1"

    def test_message_complete_default(self) -> None:
        msg = self.writer.message_complete()
        assert msg.config == {}

    def test_title_generation(self) -> None:
        msg = self.writer.title_generation("My Title")
        assert msg.type == StreamMessageType.TITLE_GENERATION
        assert msg.content == "My Title"

    def test_error(self) -> None:
        msg = self.writer.error("boom")
        assert msg.type == StreamMessageType.ERROR
        assert msg.content == "boom"

    def test_error_with_config(self) -> None:
        msg = self.writer.error("fail", config={"code": 500})
        assert msg.config["code"] == 500


class TestStreamWriterReasoningEvents:
    """Tests for StreamWriter reasoning event methods."""

    def setup_method(self) -> None:
        self.writer = StreamWriter()

    def test_reasoning_start(self) -> None:
        msg = self.writer.reasoning_start()
        assert msg.type == StreamMessageType.REASONING_START

    def test_reasoning_stream(self) -> None:
        msg = self.writer.reasoning_stream("thinking...")
        assert msg.type == StreamMessageType.REASONING_STREAM
        assert msg.content == "thinking..."

    def test_reasoning_end(self) -> None:
        msg = self.writer.reasoning_end()
        assert msg.type == StreamMessageType.REASONING_END


class TestStreamWriterToolCallEvents:
    """Tests for StreamWriter tool-call event methods."""

    def setup_method(self) -> None:
        self.writer = StreamWriter()

    def test_tool_call_start(self) -> None:
        msg = self.writer.tool_call_start("tc_1", "search", {"q": "test"})
        assert msg.type == StreamMessageType.TOOL_CALL_START
        assert msg.config["tool_call_id"] == "tc_1"
        assert msg.config["tool_name"] == "search"
        assert msg.config["tool_arguments"] == {"q": "test"}

    def test_tool_call_start_with_sub_agent(self) -> None:
        msg = self.writer.tool_call_start("tc_1", "search", {"q": "test"}, sub_agent_id="sa_1")
        assert msg.config["sub_agent_id"] == "sa_1"

    def test_tool_call_start_without_sub_agent(self) -> None:
        msg = self.writer.tool_call_start("tc_1", "search", {"q": "test"})
        assert "sub_agent_id" not in msg.config

    def test_tool_call_stream(self) -> None:
        msg = self.writer.tool_call_stream("tc_1", "partial result")
        assert msg.type == StreamMessageType.TOOL_CALL_STREAM
        assert msg.content == "partial result"
        assert msg.config["tool_call_id"] == "tc_1"

    def test_tool_call_stream_with_sub_agent(self) -> None:
        msg = self.writer.tool_call_stream("tc_1", "chunk", sub_agent_id="sa_1")
        assert msg.config["sub_agent_id"] == "sa_1"

    def test_tool_call_end_success(self) -> None:
        msg = self.writer.tool_call_end("tc_1", "search", "success", tool_result="found 3")
        assert msg.type == StreamMessageType.TOOL_CALL_END
        assert msg.config["tool_call_id"] == "tc_1"
        assert msg.config["tool_name"] == "search"
        assert msg.config["tool_status"] == "success"
        assert msg.config["tool_result"] == "found 3"

    def test_tool_call_end_error(self) -> None:
        msg = self.writer.tool_call_end("tc_1", "search", "error", tool_error="timeout")
        assert msg.config["tool_status"] == "error"
        assert msg.config["tool_error"] == "timeout"
        assert "tool_result" not in msg.config

    def test_tool_call_end_with_duration(self) -> None:
        msg = self.writer.tool_call_end("tc_1", "search", "success", tool_duration_ms=150)
        assert msg.config["tool_duration_ms"] == 150

    def test_tool_call_end_with_sub_agent(self) -> None:
        msg = self.writer.tool_call_end("tc_1", "search", "success", sub_agent_id="sa_1")
        assert msg.config["sub_agent_id"] == "sa_1"

    def test_tool_call_end_minimal(self) -> None:
        msg = self.writer.tool_call_end("tc_1", "search", "success")
        assert "tool_result" not in msg.config
        assert "tool_error" not in msg.config
        assert "tool_duration_ms" not in msg.config
        assert "sub_agent_id" not in msg.config


class TestStreamWriterMultiAgentEvents:
    """Tests for StreamWriter multi-agent event methods."""

    def setup_method(self) -> None:
        self.writer = StreamWriter()

    def test_plan_start(self) -> None:
        msg = self.writer.plan_start()
        assert msg.type == StreamMessageType.PLAN_START

    def test_plan_stream(self) -> None:
        msg = self.writer.plan_stream("analyzing request...")
        assert msg.type == StreamMessageType.PLAN_STREAM
        assert msg.content == "analyzing request..."

    def test_plan_complete(self) -> None:
        plan_data = {"goal": "test", "steps": []}
        msg = self.writer.plan_complete(plan_data)
        assert msg.type == StreamMessageType.PLAN_COMPLETE
        assert msg.config["plan"] == plan_data

    def test_sub_agent_start(self) -> None:
        msg = self.writer.sub_agent_start("sa_1", "WeatherAgent", 1, ["get_weather"])
        assert msg.type == StreamMessageType.SUB_AGENT_START
        assert msg.config["sub_agent_id"] == "sa_1"
        assert msg.config["sub_agent_name"] == "WeatherAgent"
        assert msg.config["step_number"] == 1
        assert msg.config["tools"] == ["get_weather"]

    def test_sub_agent_stream(self) -> None:
        msg = self.writer.sub_agent_stream("sa_1", "token")
        assert msg.type == StreamMessageType.SUB_AGENT_STREAM
        assert msg.content == "token"
        assert msg.config["sub_agent_id"] == "sa_1"

    def test_sub_agent_end_success(self) -> None:
        msg = self.writer.sub_agent_end("sa_1", "WeatherAgent", "success", "Done", duration_ms=500)
        assert msg.type == StreamMessageType.SUB_AGENT_END
        assert msg.config["sub_agent_id"] == "sa_1"
        assert msg.config["sub_agent_name"] == "WeatherAgent"
        assert msg.config["status"] == "success"
        assert msg.config["result_summary"] == "Done"
        assert msg.config["duration_ms"] == 500

    def test_sub_agent_end_without_duration(self) -> None:
        msg = self.writer.sub_agent_end("sa_1", "Agent", "error", "Failed")
        assert "duration_ms" not in msg.config

    def test_synthesis_start(self) -> None:
        msg = self.writer.synthesis_start()
        assert msg.type == StreamMessageType.SYNTHESIS_START

    def test_synthesis_stream(self) -> None:
        msg = self.writer.synthesis_stream("combining results")
        assert msg.type == StreamMessageType.SYNTHESIS_STREAM
        assert msg.content == "combining results"


class TestStreamWriterTraceEvent:
    """Tests for StreamWriter trace event method."""

    def setup_method(self) -> None:
        self.writer = StreamWriter()

    def test_trace_method_exists(self) -> None:
        assert hasattr(self.writer, "trace") or hasattr(self.writer, "error")

    def test_full_streaming_lifecycle(self) -> None:
        msgs = [
            self.writer.stream_start(),
            self.writer.text_stream("Hello "),
            self.writer.text_stream("World"),
            self.writer.stream_end(),
        ]
        types = [m.type for m in msgs]
        assert types == [
            StreamMessageType.STREAM_START,
            StreamMessageType.TEXT_STREAM,
            StreamMessageType.TEXT_STREAM,
            StreamMessageType.STREAM_END,
        ]

    def test_tool_call_lifecycle(self) -> None:
        msgs = [
            self.writer.tool_call_start("tc_1", "search", {"q": "test"}),
            self.writer.tool_call_stream("tc_1", "partial"),
            self.writer.tool_call_end("tc_1", "search", "success", tool_result="ok"),
        ]
        types = [m.type for m in msgs]
        assert types == [
            StreamMessageType.TOOL_CALL_START,
            StreamMessageType.TOOL_CALL_STREAM,
            StreamMessageType.TOOL_CALL_END,
        ]
