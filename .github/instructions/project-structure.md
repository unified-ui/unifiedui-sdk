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
│       ├── tracing/               # Tracing objects, LangChain/LangGraph sniffing
│       │   ├── __init__.py        # Re-exports models + tracers
│       │   ├── models.py          # Pydantic trace data models (Trace, TraceNode, etc.)
│       │   ├── base.py            # BaseTracer — shared callback logic & extension hooks
│       │   ├── langchain.py       # UnifiedUILangchainTracer (thin subclass of BaseTracer)
│       │   ├── langgraph.py       # UnifiedUILanggraphTracer (filters __start__/__end__)
│       │   └── README.md
│       ├── streaming/             # Standardized streaming responses (planned)
│       │   ├── __init__.py
│       │   └── README.md
│       └── agents/                # ReACT Agent, agent engine (planned)
│           ├── __init__.py
│           └── README.md
├── tests/                         # Test suite (mirrors src structure)
│   ├── conftest.py
│   ├── test_version.py
│   ├── README.md
│   ├── core/
│   │   └── test_utils.py
│   ├── tracing/
│   │   ├── test_models.py
│   │   ├── test_base.py
│   │   ├── test_langchain.py
│   │   └── test_langgraph.py
│   ├── streaming/
│   └── agents/
├── docs/                          # Extended documentation
├── notebooks/                     # Jupyter notebooks for experiments
├── pocs/                          # Proof-of-concept scripts
│   └── tracings/                  # Tracing POCs (002, 003)
└── .github/
    ├── workflows/                 # CI pipelines
    └── instructions/              # Copilot instruction files
```

## Naming Conventions

- **Modules**: prefer single-word names without underscores (e.g. `langchain.py`, `models.py`, `utils.py`). Use `snake_case` only when a multi-word name is unavoidable.
- **Classes**: `PascalCase` (e.g. `ReactAgent`, `StreamingResponse`)
- **Functions/Methods**: `snake_case` (e.g. `create_trace`, `stream_response`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g. `DEFAULT_TIMEOUT`)
- **Test files**: `test_<module>.py` (e.g. `test_langchain.py`, `test_models.py`)

## Module Responsibilities

### `core`
Shared abstractions that other modules depend on. Contains base classes, protocols, type aliases, and utility functions in `utils.py` (e.g. `generate_id`, `utc_now`, `safe_str`, `str_uuid`). **No external dependencies** beyond the standard library.

### `tracing`
Provides standardized tracing objects for unified-ui. Contains a `BaseTracer` with shared callback logic and extension hooks (`_resolve_name`, `_should_trace_node`), plus thin framework-specific subclasses: `UnifiedUILangchainTracer` for LangChain and `UnifiedUILanggraphTracer` for LangGraph (which filters internal `__start__`/`__end__` nodes). Pydantic models mirror the Go agent-service trace structures.

### `streaming`
Implements standardized streaming response protocols for unified-ui. Ensures consistent streaming behavior across different agent backends (LangChain, LangGraph, custom agents).

### `agents`
High-level agent abstractions. Contains the `ReactAgent` class and an agent engine built on top of LangChain/LangGraph. Designed to be the primary entry point for developers building agents.
