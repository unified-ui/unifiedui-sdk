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

## DRY (Don't Repeat Yourself)

- Extract shared logic into private helper methods (e.g. `_finalize()` for common status transitions)
- Move reusable utility functions to `core/utils.py` — never duplicate helpers across modules
- If two methods share 3+ lines of identical logic, refactor into a shared helper
- Prefer composition and delegation over copy-paste

## File & Module Naming

- **Avoid underscores** in module filenames where possible (e.g. `langchain.py` not `langchain_tracer.py`)
- Use short, descriptive single-word names: `models.py`, `langchain.py`, `utils.py`
- Test files mirror source: `test_<module>.py` (e.g. `test_langchain.py`, `test_models.py`)
- Exception: Python convention requires underscores for multi-word names that cannot be a single word

## Shared Utilities

- Place generic helpers in `core/utils.py` (e.g. `generate_id`, `utc_now`, `safe_str`, `str_uuid`)
- Domain-specific helpers stay in their module (e.g. `_extract_name` in `tracing/langchain.py`)
- Public utilities get full docstrings; module-private helpers (`_prefixed`) get a one-liner
- Export shared utilities via `core/__init__.py` with `__all__`

## Pydantic Models

- Use `Field(alias="camelCase")` for JSON serialization matching external APIs
- Set `model_config = {"populate_by_name": True}` to allow both snake_case and camelCase construction
- Use `Field(default_factory=...)` for mutable defaults and generated values
- Implement `to_dict()` as `self.model_dump(mode="json", by_alias=True, exclude_none=True)`
