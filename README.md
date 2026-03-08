# unified-ui SDK

[![CI](https://github.com/unified-ui/unifiedui-sdk/actions/workflows/ci-tests-and-lint.yml/badge.svg)](https://github.com/unified-ui/unifiedui-sdk/actions/workflows/ci-tests-and-lint.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff/)

> **Python SDK for external integration with the unified-ui platform** — tracing, streaming, agents, and more.

## What is unified-ui?

**unified-ui** transforms the complexity of managing multiple AI systems into a single, cohesive experience. Organizations deploy agents across diverse platforms — Microsoft Foundry, n8n, LangGraph, Copilot, and custom solutions — resulting in fragmented user experiences, inconsistent monitoring, and operational silos.

unified-ui eliminates these challenges by providing **one interface where every agent converges**.

## What is this SDK?

The **unified-ui SDK** is a complementary Python package that provides capabilities for **external integration** with the unified-ui platform:

| Module | Description |
|--------|-------------|
| 🔍 **Tracing** | Standardized tracing objects; LangChain & LangGraph trace sniffing and forwarding |
| 📡 **Streaming** | Standardized streaming response protocol for unified-ui |
| 🤖 **Agents** | ReACT Agent class with an agent engine built on LangChain / LangGraph |
| 🧱 **Core** | Shared interfaces, base classes, and utility functions |

### How It Fits

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│  Frontend   │────▶│         Platform Service (FastAPI)           │
└─────────────┘     │  • Authentication & RBAC                     │
                    │  • Tenants, Applications, Credentials        │
                    │  • Conversations, Autonomous Agents          │
                    └──────────────────┬───────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
     ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
     │ Agent Service  │    │ Custom Service │    │ External App   │
     │  (Go/Gin)      │    │                │    │                │
     └────────────────┘    └────────────────┘    └────────────────┘
              │                    │                      │
              │         ┌─────────┴──────────┐           │
              │         │  unifiedui-sdk ◀───┼───────────┘
              │         │  (this package)    │
              │         └────────────────────┘
              ▼
     ┌────────────────┐
     │ AI Backends    │
     │ N8N, Foundry,  │
     │ LangGraph, ... │
     └────────────────┘
```

---

## Installation

```bash
pip install unifiedui-sdk
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add unifiedui-sdk
```

---

## Quick Start

### Tracing — Capture Traces from LangChain / LangGraph

```python
from unifiedui_sdk.tracing import UnifiedUILanggraphTracer

tracer = UnifiedUILanggraphTracer()

# Attach to any LangChain/LangGraph execution
result = graph.invoke(
    {"messages": [("human", "Hello")]},
    config={"callbacks": [tracer]},
)

# Get the trace as a dict (camelCase JSON for the agent-service API)
trace_dict = tracer.get_trace_dict()
```

### Streaming — Build SSE Responses

```python
from unifiedui_sdk.streaming import StreamWriter, StreamMessageType

writer = StreamWriter()

# Build stream messages for the unified-ui SSE protocol
yield writer.stream_start()
yield writer.text_stream("Hello ")
yield writer.text_stream("world!")
yield writer.tool_call_start("tc_1", "search", {"query": "test"})
yield writer.tool_call_end("tc_1", "search", "success", tool_result="Found 3 results")
yield writer.stream_end()
```

### Agents — Single-Agent with Tools

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

engine = ReActAgentEngine(
    config=config, llm=llm, tools=[calculator], tracer=tracer
)

# Stream agent execution
async for msg in engine.invoke_stream("What is 42 * 17?"):
    if msg.type == "TEXT_STREAM":
        print(msg.content, end="", flush=True)
    elif msg.type == "TOOL_CALL_START":
        print(f"\nTool: {msg.config['tool_name']}")
    elif msg.type == "TOOL_CALL_END":
        print(f"Result: {msg.config['tool_result']}")
```

### Agents — Multi-Agent Orchestration

```python
from unifiedui_sdk.agents import ReActAgentConfig, ReActAgentEngine
from unifiedui_sdk.agents.config import MultiAgentConfig
from unifiedui_sdk.tracing import ReActAgentTracer

config = ReActAgentConfig(
    system_prompt="You are a research assistant.",
    multi_agent_enabled=True,
    multi_agent=MultiAgentConfig(
        max_sub_agents=5,
        max_parallel_per_step=3,
    ),
)

tracer = ReActAgentTracer()
engine = ReActAgentEngine(config=config, llm=llm, tools=[...], tracer=tracer)

async for msg in engine.invoke_stream("Compare weather in Berlin, Munich, Hamburg"):
    if msg.type == "PLAN_COMPLETE":
        print("Plan:", msg.config["plan"]["goal"])
    elif msg.type == "SUB_AGENT_STREAM":
        print(msg.content, end="")
    elif msg.type == "SYNTHESIS_STREAM":
        print(msg.content, end="")

# Get the full trace
trace = tracer.get_trace()
```

### Agents — Tool Loading (OpenAPI + MCP)

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
engine = ReActAgentEngine(config=config, llm=llm, tools=tools)
```

> Detailed module documentation: [`tracing/`](src/unifiedui_sdk/tracing/README.md) · [`streaming/`](src/unifiedui_sdk/streaming/README.md) · [`agents/`](src/unifiedui_sdk/agents/README.md) · [`core/`](src/unifiedui_sdk/core/README.md)

---

## Development

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended)

### Setup

```bash
# Clone the repository
git clone https://github.com/unified-ui/unifiedui-sdk.git
cd unifiedui-sdk

# Install dependencies
uv sync

# Install pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg
```

### Common Commands

| Command | Description |
|---------|-------------|
| `pytest tests/ -n auto` | Run tests in parallel |
| `pytest tests/ -n auto --cov=unifiedui_sdk --cov-fail-under=80` | Tests + coverage |
| `ruff check .` | Lint |
| `ruff format .` | Format |
| `mypy src/unifiedui_sdk/` | Type check |

> **See [TOOLING.md](TOOLING.md)** for the full tooling guide, pre-commit hooks, and CI details.

---

## Project Structure

```
unifiedui-sdk/
├── src/unifiedui_sdk/           # Main package (src layout)
│   ├── core/                    # Shared interfaces & utilities
│   │   └── utils.py             # generate_id, utc_now, safe_str, str_uuid
│   ├── tracing/                 # Tracing objects & LangChain/LangGraph sniffing
│   │   ├── models.py            # Trace, TraceNode, NodeData, NodeType, NodeStatus
│   │   ├── base.py              # BaseTracer (callback handler)
│   │   ├── langchain.py         # UnifiedUILangchainTracer
│   │   ├── langgraph.py         # UnifiedUILanggraphTracer
│   │   └── react_agent.py       # ReActAgentTracer (multi-agent trace support)
│   ├── streaming/               # Standardized streaming responses
│   │   ├── models.py            # StreamMessage, StreamMessageType (22 events)
│   │   └── writer.py            # StreamWriter (~25 builder methods)
│   └── agents/                  # ReACT Agent Engine
│       ├── config.py            # ReActAgentConfig, MultiAgentConfig, ToolConfig
│       ├── engine.py            # ReActAgentEngine (single + multi-agent)
│       ├── single.py            # Single-agent ReACT executor
│       ├── prompts.py           # System prompt builder
│       ├── tools/               # Tool integrations
│       │   ├── openapi.py       # OpenAPI 3.x → LangChain tools
│       │   ├── mcp.py           # MCP Server → LangChain tools
│       │   └── loader.py        # Parallel tool loader
│       └── multi/               # Multi-agent orchestration
│           ├── planner.py       # LLM-based execution plan generator
│           ├── executor.py      # Parallel sub-agent executor
│           ├── synthesizer.py   # Result synthesizer
│           └── orchestrator.py  # Full pipeline coordinator
├── tests/                       # Test suite (327 tests)
├── docs/                        # Documentation
├── pocs/                        # Proof-of-concept scripts
└── .github/                     # CI workflows & Copilot instructions
```

---

## Branching Strategy

This project follows a **Git Flow** branching model optimized for open-source SDK releases with semantic versioning.

```mermaid
gitGraph
    commit id: "init"
    branch develop
    checkout develop
    commit id: "setup"

    branch feat/tracing
    checkout feat/tracing
    commit id: "add tracing"
    commit id: "tracing tests"
    checkout develop
    merge feat/tracing id: "merge tracing"

    branch feat/streaming
    checkout feat/streaming
    commit id: "add streaming"
    checkout develop
    merge feat/streaming id: "merge streaming"

    branch release/0.1.0
    checkout release/0.1.0
    commit id: "bump 0.1.0"
    commit id: "fix docs"
    checkout main
    merge release/0.1.0 id: "v0.1.0" tag: "v0.1.0"
    checkout develop
    merge release/0.1.0 id: "back-merge 0.1.0"

    checkout develop
    branch feat/agents
    checkout feat/agents
    commit id: "add agents"
    checkout develop
    merge feat/agents id: "merge agents"

    checkout main
    branch hotfix/0.1.1
    checkout hotfix/0.1.1
    commit id: "critical fix"
    checkout main
    merge hotfix/0.1.1 id: "v0.1.1" tag: "v0.1.1"
    checkout develop
    merge hotfix/0.1.1 id: "back-merge hotfix"

    branch release/0.2.0
    checkout release/0.2.0
    commit id: "bump 0.2.0"
    checkout main
    merge release/0.2.0 id: "v0.2.0" tag: "v0.2.0"
    checkout develop
    merge release/0.2.0 id: "back-merge 0.2.0"
```

### Branch Types

| Branch | Purpose | Branches from | Merges into |
|--------|---------|---------------|-------------|
| `main` | Stable releases only — every commit is a tagged version | — | — |
| `develop` | Integration branch for the next release | `main` | `release/*` |
| `feat/<name>` | New features or enhancements | `develop` | `develop` |
| `fix/<name>` | Bug fixes (non-critical) | `develop` | `develop` |
| `release/<version>` | Release preparation (version bump, changelog, final fixes) | `develop` | `main` + `develop` |
| `hotfix/<version>` | Critical fixes on a released version | `main` | `main` + `develop` |
| `docs/<name>` | Documentation-only changes | `develop` | `develop` |
| `refactor/<name>` | Code restructuring without behavior changes | `develop` | `develop` |

### Workflow

1. **Feature development** — Create a `feat/` branch from `develop`. Open a PR back into `develop` when ready.
2. **Release preparation** — When `develop` is ready for a release, create a `release/x.y.z` branch. Bump the version, update the changelog, and fix any last-minute issues on this branch.
3. **Publishing** — Merge the release branch into `main` and tag it (`vx.y.z`). Back-merge into `develop`.
4. **Hotfixes** — For critical bugs on a released version, create a `hotfix/` branch from `main`, fix, tag, and back-merge into both `main` and `develop`.

### Rules

- **Never commit directly** to `main` or `develop` — always use PRs
- **All PRs require** passing CI (tests, lint, type check, coverage ≥ 80%)
- **Squash merge** feature branches into `develop` for a clean history
- **Merge commits** for release/hotfix branches to preserve branch topology
- **Tag format**: `v<major>.<minor>.<patch>` (e.g. `v0.1.0`)
- **Branch naming**: `<type>/<short-description>` (e.g. `feat/langchain-tracing`)

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our development workflow, code standards, and how to submit pull requests.

---

## Sponsors

If you find this project useful, consider [sponsoring](SPONSORS.md) its development.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
