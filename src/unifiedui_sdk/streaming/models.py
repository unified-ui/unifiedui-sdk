"""Streaming data models — StreamMessage types and Pydantic models for the unified-ui SSE protocol."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StreamMessageType(StrEnum):
    """All supported stream message types for the unified-ui SSE protocol.

    Covers core events, reasoning/tool-call events (ADR-001),
    and multi-agent orchestration events (ADR-002).
    """

    # Core events
    STREAM_START = "STREAM_START"
    TEXT_STREAM = "TEXT_STREAM"
    STREAM_NEW_MESSAGE = "STREAM_NEW_MESSAGE"
    STREAM_END = "STREAM_END"
    MESSAGE_COMPLETE = "MESSAGE_COMPLETE"
    TITLE_GENERATION = "TITLE_GENERATION"
    ERROR = "ERROR"

    # Reasoning events
    REASONING_START = "REASONING_START"
    REASONING_STREAM = "REASONING_STREAM"
    REASONING_END = "REASONING_END"

    # Tool-call events
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_STREAM = "TOOL_CALL_STREAM"
    TOOL_CALL_END = "TOOL_CALL_END"

    # Multi-agent events
    PLAN_START = "PLAN_START"
    PLAN_STREAM = "PLAN_STREAM"
    PLAN_COMPLETE = "PLAN_COMPLETE"
    SUB_AGENT_START = "SUB_AGENT_START"
    SUB_AGENT_STREAM = "SUB_AGENT_STREAM"
    SUB_AGENT_END = "SUB_AGENT_END"
    SYNTHESIS_START = "SYNTHESIS_START"
    SYNTHESIS_STREAM = "SYNTHESIS_STREAM"

    # Trace event (optional — send complete trace at stream end)
    TRACE = "TRACE"


class StreamMessage(BaseModel):
    """A single message in the unified-ui SSE stream.

    Attributes:
        type: The message type determining how the content should be handled.
        content: Text content (token chunks, reasoning text, etc.).
        config: Structured metadata (tool-call details, plan data, etc.).
    """

    type: StreamMessageType
    content: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
