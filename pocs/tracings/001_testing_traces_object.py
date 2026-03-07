"""POC 001 — Testing the Trace data objects manually."""

import json

from unifiedui_sdk.tracing import (
    NodeData,
    NodeDataIO,
    NodeStatus,
    NodeType,
    Trace,
    TraceContextType,
    TraceNode,
)


def main() -> None:
    # 1. Create a Trace manually
    trace = Trace(
        tenant_id="tenant-123",
        chat_agent_id="agent-456",
        conversation_id="conv-789",
        context_type=TraceContextType.CONVERSATION,
        reference_name="test-workflow",
    )
    trace.add_log("Starting workflow execution")

    # 2. Create a top-level chain node
    chain_node = TraceNode(
        name="AgentExecutor",
        type=NodeType.CHAIN,
    )
    chain_node.mark_running()

    # 3. Create an LLM sub-node
    llm_node = TraceNode(
        name="AzureChatOpenAI",
        type=NodeType.LLM,
        data=NodeData(
            input=NodeDataIO(text="What is the weather in Berlin?"),
        ),
    )
    llm_node.mark_running()
    llm_node.data.output = NodeDataIO(  # type: ignore[union-attr]
        text="I'll use the weather tool to check that.",
        extra_data={"tool_calls": [{"name": "get_weather", "args": {"city": "Berlin"}}]},
    )
    llm_node.mark_completed()

    # 4. Create a Tool sub-node
    tool_node = TraceNode(
        name="get_weather",
        type=NodeType.TOOL,
        data=NodeData(
            input=NodeDataIO(text='{"city": "Berlin"}'),
            output=NodeDataIO(text="Berlin: 18°C, partly cloudy"),
        ),
    )
    tool_node.mark_running()
    tool_node.mark_completed()

    # 5. Create second LLM call
    llm_node_2 = TraceNode(
        name="AzureChatOpenAI",
        type=NodeType.LLM,
        data=NodeData(
            input=NodeDataIO(text="Weather result: Berlin: 18°C, partly cloudy"),
            output=NodeDataIO(text="The weather in Berlin is 18°C and partly cloudy."),
        ),
    )
    llm_node_2.mark_running()
    llm_node_2.mark_completed()

    # 6. Assemble the tree
    chain_node.add_child(llm_node)
    chain_node.add_child(tool_node)
    chain_node.add_child(llm_node_2)
    chain_node.mark_completed()

    trace.add_node(chain_node)
    trace.add_log("Workflow execution completed")

    # 7. Serialize to dict
    trace_dict = trace.to_dict()
    print("=== Trace as Dict (camelCase JSON) ===")
    print(json.dumps(trace_dict, indent=2, default=str))

    # 8. Verify structure
    print("\n=== Verification ===")
    print(f"Trace ID: {trace.id}")
    print(f"Tenant ID: {trace.tenant_id}")
    print(f"Context Type: {trace.context_type}")
    print(f"Top-level nodes: {len(trace.nodes)}")
    print(f"Chain node children: {len(trace.nodes[0].nodes)}")
    print(f"Chain status: {trace.nodes[0].status}")
    print(f"LLM 1 duration: {trace.nodes[0].nodes[0].duration:.4f}s")
    print(f"Tool duration: {trace.nodes[0].nodes[1].duration:.4f}s")

    # 9. Verify types
    assert isinstance(trace_dict, dict)
    assert trace_dict["contextType"] == "conversation"
    assert len(trace_dict["nodes"]) == 1
    assert len(trace_dict["nodes"][0]["nodes"]) == 3
    assert trace_dict["nodes"][0]["status"] == "completed"
    assert trace_dict["nodes"][0]["nodes"][0]["type"] == "llm"
    assert trace_dict["nodes"][0]["nodes"][1]["type"] == "tool"
    print("\n✅ All assertions passed!")

    # 10. Test node status enum
    print(f"\nNodeStatus values: {[s.value for s in NodeStatus]}")
    print(f"NodeType values: {[t.value for t in NodeType]}")


if __name__ == "__main__":
    main()
