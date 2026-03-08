# unifiedui_sdk.tracing

Standardized tracing objects for unified-ui integrations with callback-based trace sniffing for LangChain, LangGraph, and the ReACT Agent Engine.

## Contents

| File | Description |
|------|-------------|
| `models.py` | Pydantic data models mirroring the agent-service trace structures |
| `base.py` | `BaseTracer(BaseCallbackHandler)` — shared callback logic and node management |
| `langchain.py` | `UnifiedUILangchainTracer` — thin subclass for LangChain workflows |
| `langgraph.py` | `UnifiedUILanggraphTracer` — subclass that filters internal graph nodes |
| `react_agent.py` | `ReActAgentTracer` — extended tracer for single and multi-agent systems |

## Architecture

```
BaseCallbackHandler (langchain-core)
        │
   BaseTracer (base.py)
   ┌────┴──────────────────────────────────────────────────────────┐
   │  • _extract_name()                                            │
   │  • _resolve_name() ← override hook                           │
   │  • _should_trace_node() ← override hook                      │
   │  • _create_node / _complete / _fail                           │
   │  • All 18 on_* callback methods                               │
   └────┬──────────────────────┬──────────────────┬────────────────┘
        │                      │                  │
   ┌────┴────┐          ┌──────┴──────┐    ┌──────┴──────────┐
   │LangChain│          │  LangGraph  │    │  ReActAgent     │
   │ Tracer  │          │  Tracer     │    │  Tracer         │
   │(no-op)  │          │  __start__  │    │  + plan nodes   │
   │         │          │  __end__    │    │  + sub-agents   │
   │         │          │  filtering  │    │  + synthesis    │
   └─────────┘          └─────────────┘    └─────────────────┘
```

## Quick Start

### LangChain

```python
from unifiedui_sdk.tracing import UnifiedUILangchainTracer

tracer = UnifiedUILangchainTracer()
result = chain.invoke({"input": "Hello"}, config={"callbacks": [tracer]})
trace_dict = tracer.get_trace_dict()  # camelCase JSON for agent-service API
```

### LangGraph

```python
from unifiedui_sdk.tracing import UnifiedUILanggraphTracer

tracer = UnifiedUILanggraphTracer()
result = graph.invoke(
    {"messages": [("human", "Hello")]},
    config={"callbacks": [tracer]},
)
trace_dict = tracer.get_trace_dict()
```

### ReACT Agent Engine

```python
from unifiedui_sdk.tracing import ReActAgentTracer
from unifiedui_sdk.agents import ReActAgentConfig, ReActAgentEngine

tracer = ReActAgentTracer()
engine = ReActAgentEngine(config=config, llm=llm, tools=tools, tracer=tracer)

async for msg in engine.invoke_stream("Hello"):
    ...  # tracer automatically captures trace data

trace = tracer.get_trace()
trace_dict = tracer.get_trace_dict()
```

## Data Models

All models use Pydantic v2 with camelCase aliases for JSON serialization:

| Model | Purpose |
|-------|---------|
| `Trace` | Root trace container with metadata and top-level nodes |
| `TraceNode` | Recursive tree node (name, type, status, duration, data, children) |
| `NodeData` | Input/output pair for a node |
| `NodeDataIO` | Text + extra data for input or output |
| `NodeStatus` | Enum: `pending`, `running`, `completed`, `failed`, `skipped`, `cancelled` |
| `NodeType` | Enum: 22 types (`agent`, `tool`, `llm`, `chain`, `retriever`, etc.) |
| `TraceContextType` | Enum: `conversation`, `autonomous_agent` |

## ReActAgentTracer

Extended tracer providing multi-agent trace support:

| Method | Description |
|--------|-------------|
| `on_plan_start()` | Creates a "Planner" trace node |
| `on_plan_created(plan_data)` | Adds the execution plan to the Planner node |
| `on_sub_agent_start(id, name, step, tools)` | Creates a "SubAgent: {name}" node |
| `on_sub_agent_end(id, status, result)` | Completes a sub-agent node |
| `on_sub_agent_tool_start(sub_id, call_id, name, args)` | Tool node as child of sub-agent |
| `on_sub_agent_tool_end(call_id, status, result, error)` | Completes tool node |
| `on_synthesis_start()` | Creates a "Synthesizer" node |
| `on_synthesis_end(response)` | Completes synthesis node |

## Extension Points

Create a custom tracer by subclassing `BaseTracer`:

```python
from unifiedui_sdk.tracing.base import BaseTracer

class MyTracer(BaseTracer):
    def _should_trace_node(self, name: str) -> bool:
        return name != "internal_noise"

    def _resolve_name(self, serialized, fallback, **kwargs):
        return kwargs.get("custom_name") or super()._resolve_name(serialized, fallback, **kwargs)
```
