# unifiedui_sdk.agents

ReACT Agent Engine with single-agent and multi-agent orchestration support, built on LangChain / LangGraph.

## Contents

| File / Directory | Description |
|------------------|-------------|
| `config.py` | Pydantic configuration models (`ReActAgentConfig`, `MultiAgentConfig`, `ToolConfig`) |
| `engine.py` | `ReActAgentEngine` — unified entry point for single and multi-agent execution |
| `single.py` | Single-agent ReACT executor using LangGraph `astream_events` v2 |
| `prompts.py` | System prompt builder with XML-tagged sections |
| `tools/openapi.py` | Converts OpenAPI 3.x specs to LangChain `StructuredTool` instances |
| `tools/mcp.py` | Connects to MCP servers (SSE / stdio) and converts tools to LangChain tools |
| `tools/loader.py` | Parallel tool loader that orchestrates OpenAPI + MCP loading |
| `multi/planner.py` | LLM-based execution plan generator with structured output |
| `multi/executor.py` | Parallel sub-agent executor with async queues and semaphores |
| `multi/synthesizer.py` | Final response synthesizer that combines sub-agent results |
| `multi/orchestrator.py` | Full multi-agent pipeline: plan → execute → synthesize |

## Architecture

```
ReActAgentEngine (engine.py)
├── Single-Agent Mode
│   └── run_single_agent (single.py)
│       └── langchain.agents.create_agent → astream_events v2
│
└── Multi-Agent Mode
    └── run_multi_agent (multi/orchestrator.py)
        ├── generate_plan (multi/planner.py)
        │   └── LLM with structured output → ExecutionPlan
        ├── execute_plan (multi/executor.py)
        │   ├── asyncio.Semaphore for parallelism
        │   ├── asyncio.Queue per task for message streaming
        │   └── create_agent per sub-agent with filtered tools
        └── synthesize (multi/synthesizer.py)
            └── LLM streaming synthesis from step results

Tool Integration:
├── openapi_to_langchain_tools (tools/openapi.py)
│   └── OpenAPI 3.x → StructuredTool with httpx
└── mcp_to_langchain_tools (tools/mcp.py)
    └── MCP Server (SSE/stdio) → StructuredTool
```

## Features

- **Single-agent mode**: Standard ReACT loop with tool calls, reasoning streaming, and text streaming
- **Multi-agent mode**: Planner → parallel executor → synthesizer pipeline
- **Tool integration**: Load tools from OpenAPI 3.x specs or MCP servers
- **Streaming**: Full SSE streaming via `StreamWriter` and `StreamMessage`
- **Tracing**: Compatible with `ReActAgentTracer` from `unifiedui_sdk.tracing`
- **Async-native**: Built on `asyncio` with `AsyncGenerator` streaming

## Quick Start

### Single-Agent

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from unifiedui_sdk.agents import ReActAgentConfig, ReActAgentEngine
from unifiedui_sdk.tracing import ReActAgentTracer


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
config = ReActAgentConfig(system_prompt="You are a helpful assistant.")
tracer = ReActAgentTracer()

engine = ReActAgentEngine(config=config, llm=llm, tools=[calculator], tracer=tracer)

# Streaming
async for msg in engine.invoke_stream("What is 42 * 17?"):
    print(msg.type, msg.content)

# Non-streaming
response = await engine.invoke("What is 42 * 17?")
```

### Multi-Agent

```python
from unifiedui_sdk.agents import ReActAgentConfig, ReActAgentEngine
from unifiedui_sdk.agents.config import MultiAgentConfig

config = ReActAgentConfig(
    system_prompt="You are a research assistant.",
    multi_agent_enabled=True,
    multi_agent=MultiAgentConfig(
        max_sub_agents=5,
        max_parallel_per_step=3,
    ),
)

engine = ReActAgentEngine(config=config, llm=llm, tools=[...])

async for msg in engine.invoke_stream("Compare weather in Berlin, Munich, Hamburg"):
    if msg.type == "PLAN_COMPLETE":
        print("Plan:", msg.config["plan"]["goal"])
    elif msg.type == "SUB_AGENT_STREAM":
        print(msg.content, end="")
    elif msg.type == "SYNTHESIS_STREAM":
        print(msg.content, end="")
```

### Tool Loading (OpenAPI + MCP)

```python
from unifiedui_sdk.agents.config import ToolConfig, ToolType, MCPTransport
from unifiedui_sdk.agents.tools.loader import load_tools

tool_configs = [
    ToolConfig(
        name="PetStore",
        type=ToolType.OPENAPI_DEFINITION,
        config={
            "spec_url": "https://petstore3.swagger.io/api/v3/openapi.json",
            "base_url": "https://petstore3.swagger.io/api/v3",
        },
    ),
    ToolConfig(
        name="MCP Weather",
        type=ToolType.MCP_SERVER,
        config={
            "url": "http://localhost:8080/sse",
            "transport": MCPTransport.SSE,
        },
    ),
]

tools = await load_tools(tool_configs)
```

## Configuration Reference

### ReActAgentConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `system_prompt` | `str \| None` | `None` | Main system instructions |
| `security_prompt` | `str \| None` | `None` | Security guardrails |
| `tool_use_prompt` | `str \| None` | `None` | Tool usage instructions |
| `response_prompt` | `str \| None` | `None` | Response format instructions |
| `max_iterations` | `int` | `15` | Max ReACT loop iterations |
| `max_execution_time_seconds` | `int` | `120` | Overall execution timeout |
| `temperature` | `float` | `0.1` | LLM temperature |
| `multi_agent_enabled` | `bool` | `False` | Enable multi-agent mode |
| `multi_agent` | `MultiAgentConfig` | defaults | Multi-agent settings |

### MultiAgentConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_sub_agents` | `int` | `5` | Max sub-agents in a plan |
| `max_parallel_per_step` | `int` | `3` | Max concurrent sub-agents per step |
| `max_planning_iterations` | `int` | `2` | Max planner retries |
| `sub_agent_max_iterations` | `int` | `10` | Max ReACT iterations per sub-agent |
| `sub_agent_max_execution_time_seconds` | `int` | `60` | Timeout per sub-agent |

## Streaming Events

The engine yields `StreamMessage` objects with these types during execution:

### Single-Agent Events

| Event | When |
|-------|------|
| `STREAM_START` | Stream begins |
| `TEXT_STREAM` | LLM text token |
| `REASONING_START/STREAM/END` | Reasoning tokens (e.g. o1-style models) |
| `TOOL_CALL_START` | Tool invocation begins |
| `TOOL_CALL_END` | Tool invocation completes (with result/error) |
| `STREAM_END` | Stream ends |
| `TRACE` | Complete trace data (if tracer attached) |

### Multi-Agent Events (additional)

| Event | When |
|-------|------|
| `PLAN_START/STREAM/COMPLETE` | Planning phase |
| `SUB_AGENT_START/STREAM/END` | Sub-agent execution |
| `SYNTHESIS_START/STREAM` | Final response synthesis |
