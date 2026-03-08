# Tests

Test suite for the unified-ui SDK, organized to mirror the `src/unifiedui_sdk/` package structure.

## Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── test_version.py             # Package version smoke test
├── core/
│   └── test_utils.py           # Tests for core utility functions
├── tracing/
│   ├── test_models.py          # Tests for Pydantic trace models
│   ├── test_base.py            # Tests for BaseTracer and _extract_name
│   ├── test_langchain.py       # Tests for UnifiedUILangchainTracer
│   └── test_langgraph.py       # Tests for UnifiedUILanggraphTracer
├── streaming/                  # (planned)
└── agents/                     # (planned)
```

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=unifiedui_sdk --cov-fail-under=80

# Parallel execution
uv run pytest tests/ -n auto
```

## Conventions

- Test files: `test_<module>.py`
- Test classes: `Test<Topic>` (e.g., `TestTracerInitialization`)
- Test functions: `test_<behavior>` (e.g., `test_default_trace`)
- Fixtures in `conftest.py` for shared setup
- No docstrings on individual test functions (disabled via ruff per-file-ignores)
