# Coding Standards

## Type Hints

- **Required** on all public functions, methods, and class attributes
- Use `from __future__ import annotations` where beneficial
- Prefer `X | None` over `Optional[X]`
- Use `typing.Protocol` for structural subtyping
- Mark the package as typed via `py.typed` (PEP 561)

## Docstrings

Follow **Google style**:

```python
def create_trace(name: str, metadata: dict[str, str] | None = None) -> Trace:
    """Create a new trace object.

    Args:
        name: Human-readable name for the trace.
        metadata: Optional key-value metadata to attach.

    Returns:
        A configured Trace instance.

    Raises:
        ValueError: If name is empty.
    """
```

## Error Handling

- Define custom exceptions in module-level `exceptions.py` files
- Inherit from a common `UnifiedUISDKError` base class
- Never catch bare `Exception` unless re-raising
- Use `raise ... from err` for exception chaining

## Imports

- Sorted automatically by ruff (isort rules)
- `unifiedui_sdk` is configured as first-party
- Use `TYPE_CHECKING` blocks for import-only-at-type-check-time dependencies
- Prefer absolute imports within the package

## General Rules

- No mutable default arguments
- No `# type: ignore` without a specific error code (e.g. `# type: ignore[override]`)
- Prefer `dataclass` or `pydantic.BaseModel` for data containers
- Use `__all__` to control public API surface in `__init__.py` files
- Keep modules focused — one primary responsibility per module
