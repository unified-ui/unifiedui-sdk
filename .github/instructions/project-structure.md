# Project Structure

## Package Layout

```
unifiedui-sdk/
├── src/
│   └── unifiedui_sdk/            # Main package (src layout)
│       ├── __init__.py            # Package metadata & public API
│       ├── py.typed               # PEP 561 type marker
│       ├── core/                  # Shared interfaces, base classes, utilities
│       │   ├── __init__.py        # Re-exports from utils.py
│       │   ├── utils.py           # Shared helpers (generate_id, utc_now, safe_str, str_uuid)
│       │   └── README.md
│       ├── tracing/               # Tracing objects, LangChain/LangGraph/ReACT agent tracing
│       │   ├── __init__.py        # Re-exports models + all tracers
│       │   ├── models.py          # Pydantic trace data models (Trace, TraceNode, etc.)
│       │   ├── base.py            # BaseTracer — shared callback logic & extension hooks
│       │   ├── langchain.py       # UnifiedUILangchainTracer (thin subclass of BaseTracer)
│       │   ├── langgraph.py       # UnifiedUILanggraphTracer (filters __start__/__end__)
│       │   ├── react_agent.py     # ReActAgentTracer (multi-agent trace support)
│       │   └── README.md
│       ├── streaming/             # Standardized streaming responses (22 SSE event types)
│       │   ├── __init__.py        # Re-exports StreamMessage, StreamMessageType, StreamWriter
│       │   ├── models.py          # StreamMessageType (StrEnum) + StreamMessage (Pydantic)
│       │   ├── writer.py          # StreamWriter (~25 builder methods)
│       │   └── README.md
│       └── agents/                # ReACT Agent Engine (single + multi-agent)
│           ├── __init__.py        # Re-exports config + engine + planner models
│           ├── config.py          # ReActAgentConfig, MultiAgentConfig, ToolConfig
│           ├── engine.py          # ReActAgentEngine (unified entry point)
│           ├── single.py          # Single-agent ReACT executor
│           ├── prompts.py         # System prompt builder with XML sections
│           ├── tools/             # Tool integrations
│           │   ├── openapi.py     # OpenAPI 3.x → LangChain StructuredTool
│           │   ├── mcp.py         # MCP Server → LangChain StructuredTool
│           │   └── loader.py      # Parallel tool loader (async)
│           ├── multi/             # Multi-agent orchestration
│           │   ├── planner.py     # LLM-based execution plan generator
│           │   ├── executor.py    # Parallel sub-agent executor
│           │   ├── synthesizer.py # Result synthesizer
│           │   └── orchestrator.py# Full pipeline: plan → execute → synthesize
│           └── README.md
├── tests/                         # Test suite (mirrors src structure, 327 tests)
│   ├── conftest.py
│   ├── test_version.py
│   ├── core/
│   │   └── test_utils.py
│   ├── tracing/
│   │   ├── test_models.py
│   │   ├── test_base.py
│   │   ├── test_langchain.py
│   │   ├── test_langgraph.py
│   │   └── test_react_agent.py
│   ├── streaming/
│   │   ├── test_models.py
│   │   └── test_writer.py
│   └── agents/
│       ├── test_config.py
│       ├── test_engine.py
│       ├── test_openapi.py
│       ├── test_mcp.py
│       ├── test_planner.py
│       └── test_prompts.py
├── docs/                          # Extended documentation
├── pocs/                          # Proof-of-concept scripts
│   ├── tracings/                  # Tracing POCs
│   └── agents/                    # Agent POCs (single + multi-agent)
└── .github/
    ├── workflows/                 # CI pipelines
    └── instructions/              # Copilot instruction files
```

## Naming Conventions

- **Modules**: prefer single-word names without underscores (e.g. `langchain.py`, `models.py`, `utils.py`). Use `snake_case` only when a multi-word name is unavoidable.
- **Classes**: `PascalCase` (e.g. `ReActAgentEngine`, `StreamWriter`)
- **Functions/Methods**: `snake_case` (e.g. `create_trace`, `stream_response`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g. `DEFAULT_TIMEOUT`)
- **Test files**: `test_<module>.py` (e.g. `test_langchain.py`, `test_models.py`)

## Module Responsibilities

### `core`
Shared abstractions that other modules depend on. Contains base classes, protocols, type aliases, and utility functions in `utils.py` (e.g. `generate_id`, `utc_now`, `safe_str`, `str_uuid`). **No external dependencies** beyond the standard library.

### `tracing`
Provides standardized tracing objects for unified-ui. Contains a `BaseTracer` with shared callback logic and extension hooks (`_resolve_name`, `_should_trace_node`), plus framework-specific subclasses: `UnifiedUILangchainTracer` for LangChain, `UnifiedUILanggraphTracer` for LangGraph (filters internal `__start__`/`__end__` nodes), and `ReActAgentTracer` for multi-agent orchestration (adds planner, sub-agent, and synthesizer trace nodes). Pydantic models mirror the Go agent-service trace structures.

### `streaming`
Implements the unified-ui SSE streaming protocol with 22 event types covering core events, reasoning, tool calls, multi-agent orchestration, and tracing. `StreamWriter` provides synchronous builder methods that construct `StreamMessage` Pydantic models without I/O.

### `agents`
ReACT Agent Engine with single-agent and multi-agent modes. `ReActAgentEngine` dispatches to `run_single_agent` (LangGraph ReACT loop) or `run_multi_agent` (planner → parallel executor → synthesizer). Tool integrations load from OpenAPI 3.x specs or MCP servers. Uses `langchain.agents.create_agent` for graph construction.
