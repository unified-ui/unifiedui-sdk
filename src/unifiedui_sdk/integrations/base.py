"""Base stream adapter — shared streaming logic for LangChain/LangGraph adapters."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from unifiedui_sdk.streaming.writer import StreamWriter

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.messages import BaseMessage

    from unifiedui_sdk.streaming.models import StreamMessage
    from unifiedui_sdk.tracing.base import BaseTracer


class BaseStreamAdapter:
    """Base adapter that maps ``astream_events`` to unified-ui ``StreamMessage`` objects.

    Subclasses provide the runnable (agent or compiled graph) and may override
    ``_skip_event`` to filter framework-internal events.

    Args:
        runnable: Any LangChain-compatible runnable that supports ``astream_events``.
        tracer: Optional tracer for unified-ui tracing.
    """

    def __init__(
        self,
        runnable: Any,
        *,
        tracer: BaseTracer | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            runnable: A LangChain-compatible runnable with ``astream_events`` support.
            tracer: Optional tracer for unified-ui tracing.
        """
        self._runnable = runnable
        self._tracer = tracer

    def _skip_event(self, event: dict[str, Any]) -> bool:
        """Return True to skip an event during streaming.

        Override in subclasses to filter framework-internal events.

        Args:
            event: A single event from ``astream_events``.

        Returns:
            True if the event should be skipped.
        """
        return False

    async def stream(
        self,
        message: str,
        message_history: list[BaseMessage] | None = None,
        *,
        config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[StreamMessage]:
        """Stream execution as unified-ui StreamMessage objects.

        Args:
            message: The user message to process.
            message_history: Optional pre-built LangChain message history.
            config: Optional additional config passed to the runnable.

        Yields:
            StreamMessage objects for the unified-ui SSE protocol.
        """
        from langchain_core.messages import HumanMessage

        writer = StreamWriter()
        callbacks: list[Any] = []
        if self._tracer:
            callbacks.append(self._tracer)

        messages: list[BaseMessage] = []
        if message_history:
            messages.extend(message_history)
        messages.append(HumanMessage(content=message))

        yield writer.stream_start(config)

        reasoning_started = False
        active_tool_calls: dict[str, float] = {}

        async for event in self._runnable.astream_events(
            {"messages": messages},
            version="v2",
            config={"callbacks": callbacks},
        ):
            if self._skip_event(event):
                continue

            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk is None:
                    continue
                if hasattr(chunk, "additional_kwargs"):
                    reasoning = chunk.additional_kwargs.get("reasoning_content", "")
                    if reasoning:
                        if not reasoning_started:
                            yield writer.reasoning_start()
                            reasoning_started = True
                        yield writer.reasoning_stream(reasoning)
                        continue

                content = chunk.content if hasattr(chunk, "content") else ""
                if content:
                    if reasoning_started:
                        yield writer.reasoning_end()
                        reasoning_started = False
                    yield writer.text_stream(str(content))

            elif kind == "on_tool_start":
                run_id = str(event.get("run_id", ""))
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                if isinstance(tool_input, str):
                    tool_input = {"input": tool_input}
                active_tool_calls[run_id] = time.time()
                yield writer.tool_call_start(
                    tool_call_id=run_id,
                    tool_name=tool_name,
                    tool_arguments=tool_input,
                )

            elif kind == "on_tool_end":
                run_id = str(event.get("run_id", ""))
                tool_name = event.get("name", "unknown")
                output = event.get("data", {}).get("output", "")
                start_time = active_tool_calls.pop(run_id, None)
                duration_ms = int((time.time() - start_time) * 1000) if start_time else None

                output_str = str(output) if not isinstance(output, str) else output
                yield writer.tool_call_end(
                    tool_call_id=run_id,
                    tool_name=tool_name,
                    tool_status="success",
                    tool_result=output_str,
                    tool_duration_ms=duration_ms,
                )

            elif kind == "on_tool_error":
                run_id = str(event.get("run_id", ""))
                tool_name = event.get("name", "unknown")
                error = str(event.get("data", {}).get("error", "Unknown error"))
                start_time = active_tool_calls.pop(run_id, None)
                duration_ms = int((time.time() - start_time) * 1000) if start_time else None

                yield writer.tool_call_end(
                    tool_call_id=run_id,
                    tool_name=tool_name,
                    tool_status="error",
                    tool_error=error,
                    tool_duration_ms=duration_ms,
                )

        if reasoning_started:
            yield writer.reasoning_end()

        yield writer.stream_end()

        if self._tracer:
            trace = self._tracer.get_trace()
            yield writer.trace(trace.to_dict())
