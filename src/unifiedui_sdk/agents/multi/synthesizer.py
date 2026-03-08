"""Synthesizer — combines sub-agent results into a final response."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models import BaseChatModel

    from unifiedui_sdk.agents.multi.planner import ExecutionPlan
    from unifiedui_sdk.streaming.models import StreamMessage
    from unifiedui_sdk.streaming.writer import StreamWriter

SYNTHESIS_SYSTEM_PROMPT = """You are a synthesis agent. Combine the results from the sub-agents
into a coherent, complete response for the user.

Original request:
{user_message}

Plan:
{plan_goal}

Sub-agent results:
{context}

Create a well-structured, comprehensive final answer. Use markdown formatting where appropriate."""


async def synthesize(
    llm: BaseChatModel,
    plan: ExecutionPlan,
    step_results: dict[str, str],
    user_message: str,
    writer: StreamWriter,
) -> AsyncGenerator[StreamMessage]:
    """Synthesize sub-agent results into a final streamed response.

    Args:
        llm: LangChain chat model instance.
        plan: The execution plan that was executed.
        step_results: Dict of task_id → result from executed tasks.
        user_message: The original user message.
        writer: StreamWriter for building stream messages.

    Yields:
        StreamMessage objects (SYNTHESIS_START + SYNTHESIS_STREAM chunks).
    """
    context_parts: list[str] = []
    for step_ in plan.steps:
        for task in step_.tasks:
            result = step_results.get(task.id, "No result")
            context_parts.append(f"### {task.name} (task_id: {task.id})\n{result}")

    context = "\n\n".join(context_parts)

    system_content = SYNTHESIS_SYSTEM_PROMPT.format(
        user_message=user_message,
        plan_goal=plan.goal,
        context=context,
    )

    yield writer.synthesis_start()

    async for chunk in llm.astream(
        [
            SystemMessage(content=system_content),
            HumanMessage(content="Create the final response."),
        ],
    ):
        content = chunk.content if hasattr(chunk, "content") else ""
        if content:
            yield writer.synthesis_stream(str(content))
