"""Stream writer — builds StreamMessage objects for the unified-ui SSE protocol."""

from __future__ import annotations

from typing import Any

from unifiedui_sdk.streaming.models import StreamMessage, StreamMessageType


class StreamWriter:
    """Builds StreamMessage objects for the unified-ui SSE streaming protocol.

    Provides convenience methods for all supported message types.
    Methods are synchronous — they only construct Pydantic models without I/O.

    Usage::

        writer = StreamWriter()
        msg = writer.stream_start()
        msg = writer.text_stream("Hello")
        msg = writer.tool_call_start("tc_1", "search", {"q": "test"})
        msg = writer.tool_call_end("tc_1", "search", "success", result="found 3")
        msg = writer.stream_end()
    """

    # --- Core events ---

    def stream_start(self, config: dict[str, Any] | None = None) -> StreamMessage:
        """Emit STREAM_START to signal the beginning of a stream."""
        return StreamMessage(type=StreamMessageType.STREAM_START, config=config or {})

    def text_stream(self, content: str) -> StreamMessage:
        """Emit TEXT_STREAM with a token chunk."""
        return StreamMessage(type=StreamMessageType.TEXT_STREAM, content=content)

    def stream_new_message(self, config: dict[str, Any] | None = None) -> StreamMessage:
        """Emit STREAM_NEW_MESSAGE to signal a new message boundary."""
        return StreamMessage(type=StreamMessageType.STREAM_NEW_MESSAGE, config=config or {})

    def stream_end(self) -> StreamMessage:
        """Emit STREAM_END to signal the end of token streaming."""
        return StreamMessage(type=StreamMessageType.STREAM_END)

    def message_complete(self, message: dict[str, Any] | None = None) -> StreamMessage:
        """Emit MESSAGE_COMPLETE with final message metadata."""
        return StreamMessage(type=StreamMessageType.MESSAGE_COMPLETE, config=message or {})

    def title_generation(self, title: str) -> StreamMessage:
        """Emit TITLE_GENERATION with a conversation title."""
        return StreamMessage(type=StreamMessageType.TITLE_GENERATION, content=title)

    def error(self, message: str, config: dict[str, Any] | None = None) -> StreamMessage:
        """Emit ERROR with an error message."""
        return StreamMessage(type=StreamMessageType.ERROR, content=message, config=config or {})

    # --- Reasoning events ---

    def reasoning_start(self) -> StreamMessage:
        """Emit REASONING_START to signal the beginning of a reasoning phase."""
        return StreamMessage(type=StreamMessageType.REASONING_START)

    def reasoning_stream(self, content: str) -> StreamMessage:
        """Emit REASONING_STREAM with a reasoning token chunk."""
        return StreamMessage(type=StreamMessageType.REASONING_STREAM, content=content)

    def reasoning_end(self) -> StreamMessage:
        """Emit REASONING_END to signal the end of a reasoning phase."""
        return StreamMessage(type=StreamMessageType.REASONING_END)

    # --- Tool-call events ---

    def tool_call_start(
        self,
        tool_call_id: str,
        tool_name: str,
        tool_arguments: dict[str, Any],
        *,
        sub_agent_id: str | None = None,
    ) -> StreamMessage:
        """Emit TOOL_CALL_START with tool name and arguments."""
        config: dict[str, Any] = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "tool_arguments": tool_arguments,
        }
        if sub_agent_id is not None:
            config["sub_agent_id"] = sub_agent_id
        return StreamMessage(type=StreamMessageType.TOOL_CALL_START, config=config)

    def tool_call_stream(
        self,
        tool_call_id: str,
        content: str,
        *,
        sub_agent_id: str | None = None,
    ) -> StreamMessage:
        """Emit TOOL_CALL_STREAM with a partial tool result chunk."""
        config: dict[str, Any] = {"tool_call_id": tool_call_id}
        if sub_agent_id is not None:
            config["sub_agent_id"] = sub_agent_id
        return StreamMessage(type=StreamMessageType.TOOL_CALL_STREAM, content=content, config=config)

    def tool_call_end(
        self,
        tool_call_id: str,
        tool_name: str,
        tool_status: str,
        *,
        tool_result: str | None = None,
        tool_error: str | None = None,
        tool_duration_ms: int | None = None,
        sub_agent_id: str | None = None,
    ) -> StreamMessage:
        """Emit TOOL_CALL_END with tool result or error."""
        config: dict[str, Any] = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "tool_status": tool_status,
        }
        if tool_result is not None:
            config["tool_result"] = tool_result
        if tool_error is not None:
            config["tool_error"] = tool_error
        if tool_duration_ms is not None:
            config["tool_duration_ms"] = tool_duration_ms
        if sub_agent_id is not None:
            config["sub_agent_id"] = sub_agent_id
        return StreamMessage(type=StreamMessageType.TOOL_CALL_END, config=config)

    # --- Multi-agent: Plan events ---

    def plan_start(self) -> StreamMessage:
        """Emit PLAN_START to signal the orchestrator begins planning."""
        return StreamMessage(type=StreamMessageType.PLAN_START)

    def plan_stream(self, content: str) -> StreamMessage:
        """Emit PLAN_STREAM with plan reasoning text."""
        return StreamMessage(type=StreamMessageType.PLAN_STREAM, content=content)

    def plan_complete(self, plan: dict[str, Any]) -> StreamMessage:
        """Emit PLAN_COMPLETE with the full execution plan."""
        return StreamMessage(type=StreamMessageType.PLAN_COMPLETE, config={"plan": plan})

    # --- Multi-agent: Sub-agent events ---

    def sub_agent_start(
        self,
        sub_agent_id: str,
        name: str,
        step_number: int,
        tools: list[str],
    ) -> StreamMessage:
        """Emit SUB_AGENT_START when a sub-agent begins execution."""
        return StreamMessage(
            type=StreamMessageType.SUB_AGENT_START,
            config={
                "sub_agent_id": sub_agent_id,
                "sub_agent_name": name,
                "step_number": step_number,
                "tools": tools,
            },
        )

    def sub_agent_stream(self, sub_agent_id: str, content: str) -> StreamMessage:
        """Emit SUB_AGENT_STREAM with a sub-agent text chunk."""
        return StreamMessage(
            type=StreamMessageType.SUB_AGENT_STREAM,
            content=content,
            config={"sub_agent_id": sub_agent_id},
        )

    def sub_agent_end(
        self,
        sub_agent_id: str,
        name: str,
        status: str,
        result_summary: str,
        *,
        duration_ms: int | None = None,
    ) -> StreamMessage:
        """Emit SUB_AGENT_END when a sub-agent completes."""
        config: dict[str, Any] = {
            "sub_agent_id": sub_agent_id,
            "sub_agent_name": name,
            "status": status,
            "result_summary": result_summary,
        }
        if duration_ms is not None:
            config["duration_ms"] = duration_ms
        return StreamMessage(type=StreamMessageType.SUB_AGENT_END, config=config)

    # --- Multi-agent: Synthesis events ---

    def synthesis_start(self) -> StreamMessage:
        """Emit SYNTHESIS_START when the synthesizer begins."""
        return StreamMessage(type=StreamMessageType.SYNTHESIS_START)

    def synthesis_stream(self, content: str) -> StreamMessage:
        """Emit SYNTHESIS_STREAM with a synthesis text chunk."""
        return StreamMessage(type=StreamMessageType.SYNTHESIS_STREAM, content=content)

    # --- Trace event ---

    def trace(self, trace_data: dict[str, Any]) -> StreamMessage:
        """Emit TRACE with the complete trace data."""
        return StreamMessage(type=StreamMessageType.TRACE, config=trace_data)
