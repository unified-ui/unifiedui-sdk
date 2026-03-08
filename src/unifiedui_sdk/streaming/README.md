# unifiedui_sdk.streaming

Standardized streaming response protocol for unified-ui integrations.

## Contents

| File | Description |
|------|-------------|
| `models.py` | `StreamMessageType` (22 event types) and `StreamMessage` (Pydantic model) |
| `writer.py` | `StreamWriter` — convenience builder for all SSE message types |

## Architecture

```
StreamMessage (models.py)
├── type: StreamMessageType     # What kind of event
├── content: str                # Text payload (tokens, reasoning, etc.)
└── config: dict[str, Any]     # Structured metadata (tool details, plan data, etc.)

StreamWriter (writer.py)
├── Core:     stream_start, text_stream, stream_end, error, message_complete
├── Reasoning: reasoning_start, reasoning_stream, reasoning_end
├── Tools:    tool_call_start, tool_call_stream, tool_call_end
├── Planning: plan_start, plan_stream, plan_complete
├── SubAgent: sub_agent_start, sub_agent_stream, sub_agent_end
├── Synthesis: synthesis_start, synthesis_stream
└── Trace:    trace
```

## Features

- **22 event types** covering the full agent lifecycle: core, reasoning, tool calls, multi-agent, and tracing
- **Synchronous writer** — methods only construct Pydantic models (no I/O)
- **Framework-agnostic** — works with any SSE transport (FastAPI, Starlette, custom)
- **Type-safe** — full `StrEnum` + Pydantic v2 validation

## Quick Start

### Building Stream Messages

```python
from unifiedui_sdk.streaming import StreamWriter, StreamMessage, StreamMessageType

writer = StreamWriter()

# Core lifecycle
yield writer.stream_start()
yield writer.text_stream("Hello ")
yield writer.text_stream("world!")
yield writer.stream_end()

# Tool calls
yield writer.tool_call_start(
    tool_call_id="tc_1",
    tool_name="search",
    tool_arguments={"query": "unified-ui"},
)
yield writer.tool_call_end(
    tool_call_id="tc_1",
    tool_name="search",
    tool_status="success",
    tool_result="Found 3 results",
    tool_duration_ms=150,
)

# Reasoning tokens (o1-style models)
yield writer.reasoning_start()
yield writer.reasoning_stream("Let me think about this...")
yield writer.reasoning_end()
```

### Consuming Stream Messages

```python
async for msg in engine.invoke_stream("Hello"):
    if msg.type == StreamMessageType.TEXT_STREAM:
        print(msg.content, end="", flush=True)
    elif msg.type == StreamMessageType.TOOL_CALL_START:
        print(f"Tool: {msg.config['tool_name']}")
    elif msg.type == StreamMessageType.TOOL_CALL_END:
        print(f"Result: {msg.config['tool_result']}")
    elif msg.type == StreamMessageType.ERROR:
        print(f"Error: {msg.content}")
```

### SSE Transport (FastAPI)

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/chat")
async def chat(message: str):
    async def event_generator():
        async for msg in engine.invoke_stream(message):
            yield f"data: {msg.model_dump_json()}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## Event Types Reference

| Category | Events | Description |
|----------|--------|-------------|
| **Core** | `STREAM_START`, `TEXT_STREAM`, `STREAM_NEW_MESSAGE`, `STREAM_END`, `MESSAGE_COMPLETE`, `TITLE_GENERATION`, `ERROR` | Basic streaming lifecycle |
| **Reasoning** | `REASONING_START`, `REASONING_STREAM`, `REASONING_END` | Reasoning/thinking tokens |
| **Tool Calls** | `TOOL_CALL_START`, `TOOL_CALL_STREAM`, `TOOL_CALL_END` | Tool invocation lifecycle |
| **Multi-Agent** | `PLAN_START`, `PLAN_STREAM`, `PLAN_COMPLETE`, `SUB_AGENT_START`, `SUB_AGENT_STREAM`, `SUB_AGENT_END`, `SYNTHESIS_START`, `SYNTHESIS_STREAM` | Multi-agent orchestration |
| **Trace** | `TRACE` | Complete trace data at stream end |
