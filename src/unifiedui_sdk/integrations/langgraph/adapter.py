"""LangGraph stream adapter — wraps a compiled LangGraph graph for unified-ui SSE streaming."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from unifiedui_sdk.streaming.writer import StreamWriter

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.messages import BaseMessage

    from unifiedui_sdk.streaming.models import StreamMessage
    from unifiedui_sdk.tracing.langgraph import UnifiedUILanggraphTracer


_INTERNAL_NODES: frozenset[str] = frozenset({"__start__", "__end__"})


class LanggraphStreamAdapter:
    """Wraps a compiled LangGraph graph for streaming via the unified-ui SSE protocol.

    Takes a pre-compiled LangGraph ``CompiledGraph`` and maps ``astream_events``
    to unified-ui ``StreamMessage`` objects.  Internal graph nodes
    (``__start__``, ``__end__``) are automatically filtered out.

    Usage::

        graph = builder.compile()
        adapter = LanggraphStreamAdapter(graph=graph)
        async for msg in adapter.stream("What is the weather?"):
            yield msg.model_dump_json()

    Args:
        graph: A compiled LangGraph graph.
        tracer: Optional LangGraph tracer for unified-ui tracing.
    """

    def __init__(
        self,
        graph: Any,
        *,
        tracer: UnifiedUILanggraphTracer | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            graph: A compiled LangGraph graph (``CompiledGraph``).
            tracer: Optional LangGraph tracer for unified-ui tracing.
        """
        self._graph = graph
        self._tracer = tracer

    async def stream(
        self,
        message: str,
        message_history: list[BaseMessage] | None = None,
        *,
        config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[StreamMessage]:
        """Stream graph execution as unified-ui StreamMessage objects.

        Args:
            message: The user message to process.
            message_history: Optional pre-built LangChain message history.
            config: Optional additional config passed to the graph.

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

        async for event in self._graph.astream_events(
            {"messages": messages},
            version="v2",
            config={"callbacks": callbacks},
        ):
            kind = event.get("event", "")
            name = event.get("name", "")

            if name in _INTERNAL_NODES:
                continue

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
