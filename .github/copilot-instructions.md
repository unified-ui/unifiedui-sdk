# Copilot Instructions — unified-ui SDK

## Project Overview

**unifiedui-sdk** is a Python SDK that provides external integration capabilities for the [unified-ui](https://github.com/unified-ui) platform. It enables developers to build AI agents and integrations that seamlessly connect with unified-ui's centralized AI management system.

## Key Modules

| Module | Purpose |
|--------|---------|
| `unifiedui_sdk.tracing` | Standardized tracing objects; LangChain, LangGraph & ReACT Agent tracing |
| `unifiedui_sdk.streaming` | Standardized streaming response protocol (22 SSE event types) |
| `unifiedui_sdk.agents` | ReACT Agent Engine with single-agent and multi-agent orchestration |
| `unifiedui_sdk.core` | Shared interfaces, base classes, and utilities |

## Tech Stack

- **Language**: Python 3.13+
- **Package Manager**: [uv](https://docs.astral.sh/uv/)
- **Testing**: pytest + pytest-cov + pytest-xdist
- **Linting/Formatting**: Ruff
- **Type Checking**: mypy (strict mode)
- **CI/CD**: GitHub Actions

## Key Files & References

| Document | Description |
|----------|-------------|
| [TOOLING.md](../../TOOLING.md) | Development tooling, commands, and quality gates |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | Contribution guidelines and workflow |
| [CHANGELOG.md](../../CHANGELOG.md) | Version history |
| [pyproject.toml](../../pyproject.toml) | Project configuration (deps, ruff, pytest, mypy, coverage) |

## Detailed Instructions

Refer to the following files for domain-specific guidance:

| Instruction File | Topic |
|------------------|-------|
| [project-structure.md](instructions/project-structure.md) | Package layout and module organization |
| [coding-standards.md](instructions/coding-standards.md) | Code style, type hints, docstrings, naming conventions |
| [testing-guide.md](instructions/testing-guide.md) | Testing patterns, coverage requirements, fixtures |

## Conventions

- **Commit messages**: [Conventional Commits](https://www.conventionalcommits.org/) — `type(scope): subject`
- **Branch names**: `<type>/<description>` (e.g. `feat/langchain-tracing`)
- **Imports**: sorted by ruff/isort; `unifiedui_sdk` is first-party
- **Docstrings**: Google style
- **Type hints**: required on ALL function signatures (every parameter and return type, public, private, nested); `py.typed` marker present; run `uv run mypy src/` — zero errors required
- **Coverage**: minimum 80%
