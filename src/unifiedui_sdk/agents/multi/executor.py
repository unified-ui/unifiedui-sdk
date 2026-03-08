"""Executor — runs sub-agent tasks with parallel execution per step."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import BaseTool

    from unifiedui_sdk.agents.multi.planner import ExecutionPlan, SubAgentTask
    from unifiedui_sdk.streaming.models import StreamMessage
    from unifiedui_sdk.streaming.writer import StreamWriter


async def execute_plan(
    plan: ExecutionPlan,
    llm: BaseChatModel,
    tools: list[BaseTool],
    writer: StreamWriter,
    step_results: dict[str, str],
    *,
    sub_agent_max_iterations: int = 10,
    max_parallel_per_step: int = 3,
    security_prompt: str = "",
    callbacks: list[Any] | None = None,
) -> AsyncGenerator[StreamMessage]:
    """Execute all steps in an execution plan, yielding stream messages.

    Args:
        plan: The execution plan to run.
        llm: LangChain chat model instance.
        tools: All available tools.
        writer: StreamWriter for building stream messages.
        step_results: Dict to store task_id → result mappings (mutated in-place).
        sub_agent_max_iterations: Max ReACT iterations per sub-agent.
        max_parallel_per_step: Max concurrent sub-agents per step.
        security_prompt: Optional security prompt for sub-agents.
        callbacks: Optional LangChain callbacks.

    Yields:
        StreamMessage objects for the SSE protocol.
    """
    for step in plan.steps:
        semaphore = asyncio.Semaphore(max_parallel_per_step)
        message_queues: dict[str, asyncio.Queue[StreamMessage | None]] = {}

        async def run_task(
            task: SubAgentTask,
            *,
            _semaphore: asyncio.Semaphore = semaphore,
            _message_queues: dict[str, asyncio.Queue[StreamMessage | None]] = message_queues,
            _step_number: int = step.step_number,
        ) -> tuple[str, str]:
            async with _semaphore:
                queue: asyncio.Queue[StreamMessage | None] = asyncio.Queue()
                _message_queues[task.id] = queue

                task_tools = [t for t in tools if t.name in task.required_tool_names]

                context_parts: list[str] = []
                for dep_id in task.depends_on:
                    if dep_id in step_results:
                        context_parts.append(f"<result task_id='{dep_id}'>\n{step_results[dep_id]}\n</result>")

                sub_prompt = task.instructions
                if context_parts:
                    sub_prompt += "\n\nContext from previous tasks:\n" + "\n".join(context_parts)
                if security_prompt:
                    sub_prompt = f"<security>\n{security_prompt}\n</security>\n\n{sub_prompt}"

                start_time = time.time()

                await queue.put(
                    writer.sub_agent_start(
                        sub_agent_id=task.id,
                        name=task.name,
                        step_number=_step_number,
                        tools=[t.name for t in task_tools],
                    )
                )

                result_parts: list[str] = []

                try:
                    from langchain.agents import create_agent

                    sub_graph = create_agent(
                        model=llm,
                        tools=task_tools,
                        system_prompt=sub_prompt,
                    )

                    async for event in sub_graph.astream_events(
                        {"messages": [HumanMessage(content=task.description)]},
                        version="v2",
                        config={},
                    ):
                        kind = event.get("event", "")

                        if kind == "on_chat_model_stream":
                            chunk = event.get("data", {}).get("chunk")
                            if chunk and hasattr(chunk, "content") and chunk.content:
                                content = str(chunk.content)
                                result_parts.append(content)
                                await queue.put(writer.sub_agent_stream(task.id, content))

                        elif kind == "on_tool_start":
                            run_id = str(event.get("run_id", ""))
                            tool_name = event.get("name", "unknown")
                            tool_input = event.get("data", {}).get("input", {})
                            if isinstance(tool_input, str):
                                tool_input = {"input": tool_input}
                            await queue.put(
                                writer.tool_call_start(
                                    tool_call_id=run_id,
                                    tool_name=tool_name,
                                    tool_arguments=tool_input,
                                    sub_agent_id=task.id,
                                )
                            )

                        elif kind == "on_tool_end":
                            run_id = str(event.get("run_id", ""))
                            tool_name = event.get("name", "unknown")
                            output = str(event.get("data", {}).get("output", ""))
                            await queue.put(
                                writer.tool_call_end(
                                    tool_call_id=run_id,
                                    tool_name=tool_name,
                                    tool_status="success",
                                    tool_result=output,
                                    sub_agent_id=task.id,
                                )
                            )

                    duration_ms = int((time.time() - start_time) * 1000)
                    result = "".join(result_parts)

                    await queue.put(
                        writer.sub_agent_end(
                            sub_agent_id=task.id,
                            name=task.name,
                            status="success",
                            result_summary=result[:500],
                            duration_ms=duration_ms,
                        )
                    )

                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    result = f"Error: {e}"
                    await queue.put(
                        writer.sub_agent_end(
                            sub_agent_id=task.id,
                            name=task.name,
                            status="error",
                            result_summary=str(e)[:500],
                            duration_ms=duration_ms,
                        )
                    )

                await queue.put(None)
                return task.id, result

        tasks_coros = [run_task(task) for task in step.tasks]

        gather_task = asyncio.ensure_future(asyncio.gather(*tasks_coros))

        active_queues: set[str] = set()
        finished_queues: set[str] = set()

        while not gather_task.done() or active_queues - finished_queues:
            await asyncio.sleep(0.01)

            for task_id, queue in list(message_queues.items()):
                if task_id not in active_queues:
                    active_queues.add(task_id)

                if task_id in finished_queues:
                    continue

                while not queue.empty():
                    msg = queue.get_nowait()
                    if msg is None:
                        finished_queues.add(task_id)
                        break
                    yield msg

        for task_id, queue in message_queues.items():
            if task_id in finished_queues:
                continue
            while not queue.empty():
                msg = queue.get_nowait()
                if msg is not None:
                    yield msg

        results = gather_task.result()
        for task_id, result in results:
            step_results[task_id] = result
