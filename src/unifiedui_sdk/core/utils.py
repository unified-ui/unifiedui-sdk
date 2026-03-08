"""Core utilities — shared helper functions used across the SDK."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any


def generate_id() -> str:
    """Generate a new UUID4 string.

    Returns:
        A new UUID4 as a string.
    """
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return the current UTC datetime.

    Returns:
        Current datetime with UTC timezone.
    """
    return datetime.now(tz=UTC)


def str_uuid(value: uuid.UUID) -> str:
    """Convert a UUID to its string representation.

    Args:
        value: The UUID to convert.

    Returns:
        String representation of the UUID.
    """
    return str(value)


def safe_str(obj: Any) -> str:
    """Convert any object to a string, handling edge cases gracefully.

    Args:
        obj: The object to convert.

    Returns:
        String representation, or empty string for None.
    """
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    try:
        return str(obj)
    except Exception:
        return repr(obj)
