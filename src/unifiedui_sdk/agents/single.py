"""Single-agent executor — LangGraph ReACT agent for single-agent mode."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from unifiedui_sdk.agents.prompts import build_system_prompt
from unifiedui_sdk.streaming.writer import StreamWriter

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import BaseTool

    from unifiedui_sdk.agents.config import ReActAgentConfig
    from unifiedui_sdk.streaming.models import StreamMessage


async def run_single_agent(
    llm: BaseChatModel,
    tools: list[BaseTool],
    config: ReActAgentConfig,
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    writer: StreamWriter | None = None,
    callbacks: list[Any] | None = None,
) -> AsyncGenerator[StreamMessage]:
    """Execute a single-agent ReACT loop using LangGraph and stream results.

    Args:
        llm: LangChain chat model instance.
        tools: List of LangChain tools available to the agent.
        config: Agent configuration.
        message: User message to process.
        history: Optional conversation history as list of {role, content} dicts.
        writer: Optional StreamWriter for building messages (creates one if not provided).
        callbacks: Optional LangChain callbacks (e.g. tracers).

    Yields:
        StreamMessage objects for the SSE protocol.
    """
    from langchain.agents import create_agent

    sw = writer or StreamWriter()
    system_prompt = build_system_prompt(config)

    graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    messages: list[Any] = []
    if history:
        for entry in history:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                from langchain_core.messages import AIMessage

                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))
    messages.append(HumanMessage(content=message))

    yield sw.stream_start()

    reasoning_started = False
    active_tool_calls: dict[str, float] = {}

    async for event in graph.astream_events(
        {"messages": messages},
        version="v2",
        config={"callbacks": callbacks or []},
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
                        yield sw.reasoning_start()
                        reasoning_started = True
                    yield sw.reasoning_stream(reasoning)
                    continue

            content = chunk.content if hasattr(chunk, "content") else ""
            if content:
                if reasoning_started:
                    yield sw.reasoning_end()
                    reasoning_started = False
                yield sw.text_stream(str(content))

        elif kind == "on_tool_start":
            run_id = str(event.get("run_id", ""))
            tool_name = event.get("name", "unknown")
            tool_input = event.get("data", {}).get("input", {})
            if isinstance(tool_input, str):
                tool_input = {"input": tool_input}
            active_tool_calls[run_id] = time.time()
            yield sw.tool_call_start(
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
            yield sw.tool_call_end(
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

            yield sw.tool_call_end(
                tool_call_id=run_id,
                tool_name=tool_name,
                tool_status="error",
                tool_error=error,
                tool_duration_ms=duration_ms,
            )

    if reasoning_started:
        yield sw.reasoning_end()

    yield sw.stream_end()
