"""SharePoint capabilities and enforcement decorator."""

from __future__ import annotations

from enum import StrEnum
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, Protocol, TypeVar

from unifiedui_sdk.tools.m365.sharepoint.exceptions import (
    SharePointCapabilityError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

P = ParamSpec("P")
R = TypeVar("R")


class _HasCapabilities(Protocol):
    """Protocol for objects with _capabilities attribute."""

    _capabilities: set[SharePointCapability]


class SharePointCapability(StrEnum):
    """Controls which features are available on the client."""

    SITES_READ = "sites_read"
    DRIVES_READ = "drives_read"
    DRIVES_WRITE = "drives_write"
    PAGES_READ = "pages_read"
    LISTS_READ = "lists_read"
    LISTS_WRITE = "lists_write"
    ONENOTE_READ = "onenote_read"
    SEARCH = "search"


def requires_capability(
    *capabilities: SharePointCapability,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator enforcing required capability for a method."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            instance: Any = args[0]
            enabled: set[SharePointCapability] = instance._capabilities
            for capability in capabilities:
                if capability not in enabled:
                    raise SharePointCapabilityError(capability.value)
            return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = ["SharePointCapability", "requires_capability"]
