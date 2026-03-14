"""LangChain stream adapter — wraps a LangChain Runnable for unified-ui SSE streaming."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from unifiedui_sdk.streaming.writer import StreamWriter

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage
    from langchain_core.tools import BaseTool

    from unifiedui_sdk.streaming.models import StreamMessage
    from unifiedui_sdk.tracing.langchain import UnifiedUILangchainTracer


class LangchainStreamAdapter:
    """Wraps a LangChain agent/chain for streaming via the unified-ui SSE protocol.

    Takes a LangChain chat model and tools, builds a ReACT agent internally,
    and maps ``astream_events`` to unified-ui ``StreamMessage`` objects.

    Usage::

        adapter = LangchainStreamAdapter(llm=chat_model, tools=[tool1, tool2])
        async for msg in adapter.stream("What is the weather?"):
            yield msg.model_dump_json()

    Args:
        llm: A LangChain chat model.
        tools: List of LangChain tools for the agent.
        system_prompt: Optional system prompt for the agent.
        tracer: Optional LangChain tracer for unified-ui tracing.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: list[BaseTool],
        *,
        system_prompt: str | None = None,
        tracer: UnifiedUILangchainTracer | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            llm: A LangChain chat model.
            tools: List of LangChain tools for the agent.
            system_prompt: Optional system prompt for the agent.
            tracer: Optional LangChain tracer for unified-ui tracing.
        """
        self._llm = llm
        self._tools = tools
        self._system_prompt = system_prompt
        self._tracer = tracer

    async def stream(
        self,
        message: str,
        message_history: list[BaseMessage] | None = None,
        *,
        config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[StreamMessage, None]:
        """Stream agent execution as unified-ui StreamMessage objects.

        Args:
            message: The user message to process.
            message_history: Optional pre-built LangChain message history.
            config: Optional additional config passed to the agent.

        Yields:
            StreamMessage objects for the unified-ui SSE protocol.
        """
        from langchain.agents import create_agent
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        writer = StreamWriter()
        callbacks: list[Any] = []
        if self._tracer:
            callbacks.append(self._tracer)

        graph = create_agent(
            model=self._llm,
            tools=self._tools,
            system_prompt=self._system_prompt or "",
        )

        messages: list[BaseMessage] = []
        if message_history:
            messages.extend(message_history)
        else:
            if self._system_prompt:
                messages.append(SystemMessage(content=self._system_prompt))
        messages.append(HumanMessage(content=message))

        yield writer.stream_start(config)

        async for msg in _stream_events(graph, messages, writer, callbacks):
            yield msg

        if self._tracer:
            trace = self._tracer.get_trace()
            yield writer.trace(trace.to_dict())

    async def stream_from_messages(
        self,
        messages: list[BaseMessage],
        *,
        config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[StreamMessage, None]:
        """Stream agent execution from a pre-built message list.

        Args:
            messages: Full message list including system/user/assistant messages.
            config: Optional additional config.

        Yields:
            StreamMessage objects for the unified-ui SSE protocol.
        """
        from langchain.agents import create_agent

        writer = StreamWriter()
        callbacks: list[Any] = []
        if self._tracer:
            callbacks.append(self._tracer)

        graph = create_agent(
            model=self._llm,
            tools=self._tools,
            system_prompt=self._system_prompt or "",
        )

        yield writer.stream_start(config)

        async for msg in _stream_events(graph, messages, writer, callbacks):
            yield msg

        if self._tracer:
            trace = self._tracer.get_trace()
            yield writer.trace(trace.to_dict())


async def _stream_events(
    graph: Any,
    messages: list[Any],
    writer: StreamWriter,
    callbacks: list[Any],
) -> AsyncGenerator[StreamMessage, None]:
    """Map LangChain astream_events to unified-ui StreamMessage objects.

    Args:
        graph: The compiled LangChain/LangGraph agent.
        messages: Input messages for the agent.
        writer: StreamWriter for building StreamMessage objects.
        callbacks: LangChain callbacks list.

    Yields:
        StreamMessage objects.
    """
    reasoning_started = False
    active_tool_calls: dict[str, float] = {}

    async for event in graph.astream_events(
        {"messages": messages},
        version="v2",
        config={"callbacks": callbacks},
    ):
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
