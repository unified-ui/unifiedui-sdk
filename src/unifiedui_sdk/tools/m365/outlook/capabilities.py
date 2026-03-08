"""Outlook capabilities and enforcement decorator."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import ParamSpec, TypeVar

from unifiedui_sdk.tools.m365.outlook.exceptions import OutlookCapabilityError

P = ParamSpec("P")
R = TypeVar("R")


class OutlookCapability(str, Enum):
    """Controls which features are available on the client."""

    MAIL_READ = "mail_read"
    MAIL_SEND = "mail_send"
    MAIL_MANAGE = "mail_manage"
    CALENDAR_READ = "calendar_read"
    CALENDAR_WRITE = "calendar_write"


def requires_capability(
    *capabilities: OutlookCapability,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator enforcing required capability for a method."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            instance = args[0]
            enabled: set[OutlookCapability] = instance._capabilities
            for capability in capabilities:
                if capability not in enabled:
                    raise OutlookCapabilityError(capability.value)
            return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = ["OutlookCapability", "requires_capability"]
