"""Tests for ReActAgentTracer."""

from __future__ import annotations

from unifiedui_sdk.tracing.models import NodeStatus, NodeType
from unifiedui_sdk.tracing.react_agent import ReActAgentTracer


class TestReActAgentTracerPlanPhase:
    """Tests for plan-related tracer events."""

    def test_on_plan_start_creates_node(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_plan_start()
        trace = tracer.get_trace()
        assert len(trace.nodes) == 1
        node = trace.nodes[0]
        assert node.name == "Planner"
        assert node.type == NodeType.AGENT
        assert node.status == NodeStatus.RUNNING

    def test_on_plan_created_completes_node(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_plan_start()
        plan_data = {
            "goal": "Find weather",
            "reasoning": "User asked for weather",
            "steps": [{"step_number": 1, "tasks": []}],
            "estimated_complexity": "simple",
        }
        tracer.on_plan_created(plan_data)
        trace = tracer.get_trace()
        node = trace.nodes[0]
        assert node.status == NodeStatus.COMPLETED
        assert node.data is not None
        assert node.data.output is not None
        assert node.data.output.text == "Find weather"
        assert node.data.output.extra_data["plan"] == plan_data

    def test_on_plan_created_stores_metadata(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_plan_start()
        plan_data = {"goal": "G", "reasoning": "R", "steps": []}
        tracer.on_plan_created(plan_data)
        trace = tracer.get_trace()
        node = trace.nodes[0]
        assert node.metadata["plan_goal"] == "G"
        assert node.metadata["plan_reasoning"] == "R"


class TestReActAgentTracerSubAgentPhase:
    """Tests for sub-agent related tracer events."""

    def test_on_sub_agent_start_creates_node(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_sub_agent_start("sa_1", "WeatherAgent", 1, ["get_weather"])
        trace = tracer.get_trace()
        assert len(trace.nodes) == 1
        node = trace.nodes[0]
        assert node.name == "SubAgent: WeatherAgent"
        assert node.type == NodeType.AGENT
        assert node.status == NodeStatus.RUNNING
        assert node.metadata["sub_agent_id"] == "sa_1"
        assert node.metadata["step_number"] == 1
        assert node.metadata["assigned_tools"] == ["get_weather"]

    def test_on_sub_agent_end_success(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_sub_agent_start("sa_1", "Agent", 1, [])
        tracer.on_sub_agent_end("sa_1", "success", "Weather is sunny")
        trace = tracer.get_trace()
        node = trace.nodes[0]
        assert node.status == NodeStatus.COMPLETED
        assert node.data is not None
        assert node.data.output is not None
        assert node.data.output.text == "Weather is sunny"

    def test_on_sub_agent_end_error(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_sub_agent_start("sa_1", "Agent", 1, [])
        tracer.on_sub_agent_end("sa_1", "error", "Timeout")
        trace = tracer.get_trace()
        node = trace.nodes[0]
        assert node.status == NodeStatus.FAILED

    def test_on_sub_agent_end_unknown_id_ignored(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_sub_agent_end("unknown", "success", "result")
        trace = tracer.get_trace()
        assert len(trace.nodes) == 0


class TestReActAgentTracerSubAgentTools:
    """Tests for tool calls within sub-agents."""

    def test_tool_start_under_sub_agent(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_sub_agent_start("sa_1", "Agent", 1, ["search"])
        tracer.on_sub_agent_tool_start("sa_1", "tc_1", "search", {"q": "test"})
        trace = tracer.get_trace()
        parent = trace.nodes[0]
        assert len(parent.nodes) == 1
        tool_node = parent.nodes[0]
        assert tool_node.name == "search"
        assert tool_node.type == NodeType.TOOL
        assert tool_node.status == NodeStatus.RUNNING

    def test_tool_end_success(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_sub_agent_start("sa_1", "Agent", 1, ["search"])
        tracer.on_sub_agent_tool_start("sa_1", "tc_1", "search", {"q": "test"})
        tracer.on_sub_agent_tool_end("tc_1", "success", tool_result="found 5")
        trace = tracer.get_trace()
        tool_node = trace.nodes[0].nodes[0]
        assert tool_node.status == NodeStatus.COMPLETED
        assert tool_node.data is not None
        assert tool_node.data.output is not None
        assert tool_node.data.output.text == "found 5"

    def test_tool_end_error(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_sub_agent_start("sa_1", "Agent", 1, ["search"])
        tracer.on_sub_agent_tool_start("sa_1", "tc_1", "search", {"q": "test"})
        tracer.on_sub_agent_tool_end("tc_1", "error", tool_error="timeout")
        trace = tracer.get_trace()
        tool_node = trace.nodes[0].nodes[0]
        assert tool_node.status == NodeStatus.FAILED

    def test_tool_start_unknown_parent_ignored(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_sub_agent_tool_start("unknown", "tc_1", "search", {})
        trace = tracer.get_trace()
        assert len(trace.nodes) == 0

    def test_tool_end_unknown_id_ignored(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_sub_agent_tool_end("unknown_tc", "success")
        trace = tracer.get_trace()
        assert len(trace.nodes) == 0


class TestReActAgentTracerSynthesisPhase:
    """Tests for synthesis-related tracer events."""

    def test_on_synthesis_start_creates_node(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_synthesis_start()
        trace = tracer.get_trace()
        assert len(trace.nodes) == 1
        node = trace.nodes[0]
        assert node.name == "Synthesizer"
        assert node.type == NodeType.AGENT
        assert node.status == NodeStatus.RUNNING

    def test_on_synthesis_end_completes_node(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_synthesis_start()
        tracer.on_synthesis_end("Final answer here")
        trace = tracer.get_trace()
        node = trace.nodes[0]
        assert node.status == NodeStatus.COMPLETED
        assert node.data is not None
        assert node.data.output is not None
        assert node.data.output.text == "Final answer here"
        assert node.data.output.extra_data["response_length"] == 17

    def test_on_synthesis_end_truncates_long_response(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_synthesis_start()
        long_response = "x" * 600
        tracer.on_synthesis_end(long_response)
        trace = tracer.get_trace()
        node = trace.nodes[0]
        assert node.data is not None
        assert node.data.output is not None
        assert len(node.data.output.text) == 500
        assert node.data.output.extra_data["response_length"] == 600

    def test_on_synthesis_end_without_start_ignored(self) -> None:
        tracer = ReActAgentTracer()
        tracer.on_synthesis_end("response")
        trace = tracer.get_trace()
        assert len(trace.nodes) == 0


class TestReActAgentTracerFullPipeline:
    """Integration-level tests covering a full multi-agent trace lifecycle."""

    def test_full_pipeline_trace(self) -> None:
        tracer = ReActAgentTracer()

        tracer.on_plan_start()
        tracer.on_plan_created({"goal": "G", "steps": [{"step_number": 1, "tasks": []}]})

        tracer.on_sub_agent_start("sa_1", "Agent1", 1, ["tool_a"])
        tracer.on_sub_agent_tool_start("sa_1", "tc_1", "tool_a", {"arg": "val"})
        tracer.on_sub_agent_tool_end("tc_1", "success", tool_result="result_a")
        tracer.on_sub_agent_end("sa_1", "success", "Done A")

        tracer.on_sub_agent_start("sa_2", "Agent2", 1, ["tool_b"])
        tracer.on_sub_agent_end("sa_2", "success", "Done B")

        tracer.on_synthesis_start()
        tracer.on_synthesis_end("Combined answer")

        trace = tracer.get_trace()
        assert len(trace.nodes) == 4

        planner = trace.nodes[0]
        assert planner.name == "Planner"
        assert planner.status == NodeStatus.COMPLETED

        sa1 = trace.nodes[1]
        assert sa1.name == "SubAgent: Agent1"
        assert len(sa1.nodes) == 1
        assert sa1.nodes[0].name == "tool_a"

        sa2 = trace.nodes[2]
        assert sa2.name == "SubAgent: Agent2"
        assert len(sa2.nodes) == 0

        synth = trace.nodes[3]
        assert synth.name == "Synthesizer"
        assert synth.status == NodeStatus.COMPLETED

    def test_should_trace_node_filters_internal(self) -> None:
        tracer = ReActAgentTracer()
        assert tracer._should_trace_node("agent") is True
        assert tracer._should_trace_node("__start__") is False
        assert tracer._should_trace_node("__end__") is False

    def test_get_trace_returns_trace_object(self) -> None:
        tracer = ReActAgentTracer()
        trace = tracer.get_trace()
        assert trace is not None
        assert hasattr(trace, "nodes")
        assert hasattr(trace, "to_dict")
