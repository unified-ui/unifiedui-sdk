"""ReACT agent tracer — extended tracer for single and multi-agent systems.

Part of the ``unifiedui_sdk.tracing`` module. Extends BaseTracer with
orchestrator-level nodes (planner, synthesizer) and sub-agent trace subtrees.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from unifiedui_sdk.core.utils import generate_id, utc_now
from unifiedui_sdk.tracing.base import BaseTracer
from unifiedui_sdk.tracing.models import (
    NodeData,
    NodeDataIO,
    NodeStatus,
    NodeType,
    Trace,
    TraceNode,
)

if TYPE_CHECKING:
    from unifiedui_sdk.streaming.writer import StreamWriter


class ReActAgentTracer(BaseTracer):
    """Extended tracer for ReACT Agent Engine with multi-agent support.

    Extends the base LangGraph tracer with:

    - Orchestrator-level trace nodes (planner, executor, synthesizer).
    - Sub-agent trace subtrees with correct parent-child relationships.
    - ExecutionPlan as metadata on plan nodes.
    - Optional StreamWriter coupling for dual-use (trace + stream).

    Compatible with both single-agent and multi-agent modes.

    Usage::

        tracer = ReActAgentTracer(stream_writer=writer)
        engine = ReActAgentEngine(config=config, llm=llm, tools=tools, tracer=tracer)
        async for msg in engine.invoke_stream("Hello"):
            ...
        trace = tracer.get_trace()
    """

    _INTERNAL_NODES: frozenset[str] = frozenset({"__start__", "__end__"})

    def __init__(
        self,
        trace: Trace | None = None,
        *,
        stream_writer: StreamWriter | None = None,
    ) -> None:
        """Initialize the ReACT agent tracer.

        Args:
            trace: Optional pre-configured Trace object.
            stream_writer: Optional StreamWriter for dual-use tracing + streaming.
        """
        super().__init__(trace=trace)
        self._stream_writer = stream_writer
        self._orchestrator_nodes: dict[str, TraceNode] = {}
        self._sub_agent_nodes: dict[str, TraceNode] = {}
        self._sub_agent_start_times: dict[str, float] = {}
        self._plan_data: dict[str, Any] | None = None

    def _should_trace_node(self, name: str) -> bool:
        """Skip internal LangGraph graph nodes."""
        return name not in self._INTERNAL_NODES

    # --- Orchestrator-level events ---

    def on_plan_start(self) -> None:
        """Record the start of the planning phase."""
        node = TraceNode(
            id=generate_id(),
            name="Planner",
            type=NodeType.AGENT,
            status=NodeStatus.RUNNING,
            start_at=utc_now(),
        )
        self._orchestrator_nodes["planner"] = node
        self._trace.add_node(node)

    def on_plan_created(self, plan_data: dict[str, Any]) -> None:
        """Record the completed execution plan.

        Args:
            plan_data: The execution plan as a dict.
        """
        self._plan_data = plan_data
        node = self._orchestrator_nodes.get("planner")
        if node:
            node.data = NodeData(
                output=NodeDataIO(
                    text=plan_data.get("goal", ""),
                    extra_data={
                        "plan": plan_data,
                        "total_steps": len(plan_data.get("steps", [])),
                        "estimated_complexity": plan_data.get("estimated_complexity", ""),
                    },
                ),
            )
            node.metadata["plan_goal"] = plan_data.get("goal", "")
            node.metadata["plan_reasoning"] = plan_data.get("reasoning", "")
            node.mark_completed()

    # --- Sub-agent events ---

    def on_sub_agent_start(
        self,
        sub_agent_id: str,
        name: str,
        step_number: int,
        tools: list[str],
    ) -> None:
        """Start a sub-agent trace subtree.

        Args:
            sub_agent_id: Unique identifier for this sub-agent task.
            name: Human-readable name of the sub-agent.
            step_number: Which execution step this sub-agent belongs to.
            tools: List of tool names assigned to this sub-agent.
        """
        node = TraceNode(
            id=generate_id(),
            name=f"SubAgent: {name}",
            type=NodeType.AGENT,
            status=NodeStatus.RUNNING,
            start_at=utc_now(),
            metadata={
                "sub_agent_id": sub_agent_id,
                "step_number": step_number,
                "assigned_tools": tools,
            },
        )
        self._sub_agent_nodes[sub_agent_id] = node
        self._sub_agent_start_times[sub_agent_id] = time.time()
        self._trace.add_node(node)

    def on_sub_agent_end(
        self,
        sub_agent_id: str,
        status: str,
        result_summary: str,
    ) -> None:
        """Complete a sub-agent trace subtree.

        Args:
            sub_agent_id: The sub-agent's task identifier.
            status: Completion status ("success" or "error").
            result_summary: Summary of the sub-agent's output.
        """
        node = self._sub_agent_nodes.get(sub_agent_id)
        if node is None:
            return

        start_time = self._sub_agent_start_times.pop(sub_agent_id, None)
        duration_ms = int((time.time() - start_time) * 1000) if start_time else 0

        node.data = NodeData(
            output=NodeDataIO(
                text=result_summary,
                extra_data={"status": status, "duration_ms": duration_ms},
            ),
        )

        if status == "success":
            node.mark_completed()
        else:
            node.mark_failed(error=result_summary)

    def on_sub_agent_tool_start(
        self,
        sub_agent_id: str,
        tool_call_id: str,
        tool_name: str,
        tool_arguments: dict[str, Any],
    ) -> None:
        """Record a tool call within a sub-agent.

        Args:
            sub_agent_id: The owning sub-agent.
            tool_call_id: Unique tool call identifier.
            tool_name: Name of the tool being called.
            tool_arguments: Arguments passed to the tool.
        """
        parent = self._sub_agent_nodes.get(sub_agent_id)
        if parent is None:
            return

        tool_node = TraceNode(
            id=tool_call_id,
            name=tool_name,
            type=NodeType.TOOL,
            status=NodeStatus.RUNNING,
            start_at=utc_now(),
            data=NodeData(
                input=NodeDataIO(
                    text=str(tool_arguments),
                    extra_data={"arguments": tool_arguments},
                ),
            ),
            metadata={"sub_agent_id": sub_agent_id},
        )
        parent.add_child(tool_node)
        self._node_map[tool_call_id] = tool_node

    def on_sub_agent_tool_end(
        self,
        tool_call_id: str,
        tool_status: str,
        tool_result: str | None = None,
        tool_error: str | None = None,
    ) -> None:
        """Complete a tool call within a sub-agent.

        Args:
            tool_call_id: The tool call identifier.
            tool_status: "success" or "error".
            tool_result: The tool's output (on success).
            tool_error: Error message (on failure).
        """
        node = self._node_map.get(tool_call_id)
        if node is None:
            return

        output_text = tool_result or tool_error or ""
        node.data = node.data or NodeData()
        node.data.output = NodeDataIO(
            text=output_text,
            extra_data={"status": tool_status},
        )

        if tool_status == "success":
            node.mark_completed()
        else:
            node.mark_failed(error=tool_error)

    # --- Synthesis events ---

    def on_synthesis_start(self) -> None:
        """Record the start of the synthesis phase."""
        node = TraceNode(
            id=generate_id(),
            name="Synthesizer",
            type=NodeType.AGENT,
            status=NodeStatus.RUNNING,
            start_at=utc_now(),
        )
        self._orchestrator_nodes["synthesizer"] = node
        self._trace.add_node(node)

    def on_synthesis_end(self, final_response: str) -> None:
        """Complete the synthesis phase.

        Args:
            final_response: The final synthesized response text.
        """
        node = self._orchestrator_nodes.get("synthesizer")
        if node is None:
            return

        node.data = NodeData(
            output=NodeDataIO(
                text=final_response[:500],
                extra_data={"response_length": len(final_response)},
            ),
        )
        node.mark_completed()
