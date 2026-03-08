# Testing Guide

## Framework & Tools

| Tool | Purpose |
|------|---------|
| pytest | Test runner |
| pytest-cov | Coverage measurement |
| pytest-xdist | Parallel test execution |
| pytest-asyncio | Async test support |

## Running Tests

> **IMPORTANT**: Always run pytest with `-n auto` to enable parallel test execution via pytest-xdist.
> This significantly speeds up test runs and is required in CI.

```bash
# All tests (parallel, quiet)
pytest tests/ -n auto --no-header -q

# With coverage report
pytest tests/ -n auto --cov=unifiedui_sdk --cov-report=html --cov-fail-under=80

# Specific module (still use -n auto)
pytest tests/tracing/ -n auto -v

# By marker
pytest tests/ -n auto -m unit
pytest tests/ -n auto -m "not slow"

# Single test file (parallel still beneficial)
pytest tests/tracing/test_spans.py -n auto
```

## Directory Structure

Tests mirror the source package layout:

```
tests/
├── conftest.py          # Shared fixtures
├── test_version.py      # Package-level smoke tests
├── core/
│   └── test_*.py
├── tracing/
│   └── test_*.py
├── streaming/
│   └── test_*.py
└── agents/
    └── test_*.py
```

## Conventions

- **File naming**: `test_<module>.py`
- **Function naming**: `test_<behavior_under_test>` — be descriptive
- **Markers**: use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Fixtures**: place shared fixtures in `conftest.py` at the appropriate level
- **Coverage**: minimum **80%** — CI will fail below this threshold

## Patterns

### Unit Tests

```python
def test_trace_creation_with_defaults() -> None:
    """Trace should be created with sensible defaults."""
    trace = create_trace(name="test")
    assert trace.name == "test"
    assert trace.metadata == {}
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_stream_response() -> None:
    """Streaming should yield all chunks."""
    chunks = [chunk async for chunk in stream("hello")]
    assert len(chunks) > 0
```

### Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("input_val,expected", [
    ("hello", True),
    ("", False),
    (None, False),
])
def test_validate_name(input_val: str | None, expected: bool) -> None:
    assert validate_name(input_val) == expected
```
