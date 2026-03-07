# Project Structure

## Package Layout

```
unifiedui-sdk/
├── src/
│   └── unifiedui_sdk/            # Main package (src layout)
│       ├── __init__.py            # Package metadata & public API
│       ├── py.typed               # PEP 561 type marker
│       ├── core/                  # Shared interfaces, base classes, utilities
│       │   └── __init__.py
│       ├── tracing/               # Tracing objects, LangChain/LangGraph sniffing
│       │   └── __init__.py
│       ├── streaming/             # Standardized streaming responses
│       │   └── __init__.py
│       └── agents/                # ReACT Agent, agent engine (LangChain/LangGraph)
│           └── __init__.py
├── tests/                         # Test suite (mirrors src structure)
│   ├── conftest.py
│   ├── test_version.py
│   ├── core/
│   ├── tracing/
│   ├── streaming/
│   └── agents/
├── docs/                          # Extended documentation
├── notebooks/                     # Jupyter notebooks for experiments
├── pocs/                          # Proof-of-concept scripts
└── .github/
    ├── workflows/                 # CI pipelines
    └── instructions/              # Copilot instruction files
```

## Naming Conventions

- **Modules**: `snake_case` (e.g. `tracing_handler.py`)
- **Classes**: `PascalCase` (e.g. `ReactAgent`, `StreamingResponse`)
- **Functions/Methods**: `snake_case` (e.g. `create_trace`, `stream_response`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g. `DEFAULT_TIMEOUT`)
- **Test files**: `test_<module>.py` (e.g. `test_tracing_handler.py`)

## Module Responsibilities

### `core`
Shared abstractions that other modules depend on. Contains base classes, protocols, type aliases, and utility functions. **No external dependencies** beyond the standard library.

### `tracing`
Provides standardized tracing objects for unified-ui. Includes callback handlers for LangChain and LangGraph that capture execution traces and forward them to the platform service.

### `streaming`
Implements standardized streaming response protocols for unified-ui. Ensures consistent streaming behavior across different agent backends (LangChain, LangGraph, custom agents).

### `agents`
High-level agent abstractions. Contains the `ReactAgent` class and an agent engine built on top of LangChain/LangGraph. Designed to be the primary entry point for developers building agents.
