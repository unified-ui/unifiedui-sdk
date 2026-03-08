# unifiedui_sdk.core

Shared utilities and helper functions used across all SDK modules.

## Contents

| File | Description |
|------|-------------|
| `utils.py` | Helper functions: `generate_id`, `utc_now`, `safe_str`, `str_uuid` |

## API

```python
from unifiedui_sdk.core import generate_id, utc_now, safe_str, str_uuid
```

| Function | Purpose |
|----------|---------|
| `generate_id()` | Generate a new UUID4 string |
| `utc_now()` | Current UTC datetime (timezone-aware) |
| `safe_str(obj)` | Convert any object to string, handles `None` and broken `__str__` |
| `str_uuid(value)` | Convert a `uuid.UUID` to its string representation |

## Design Decisions

- **No external dependencies** — `core` only uses the Python standard library
- All functions are pure and side-effect free (except `generate_id` and `utc_now` which use system state)
- Used as `default_factory` values in Pydantic models throughout the SDK
