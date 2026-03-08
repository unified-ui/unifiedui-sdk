"""unified-ui SDK — Python SDK for external integration with the unified-ui platform."""

from importlib.metadata import version

from unifiedui_sdk.client.client import UnifiedUIClient
from unifiedui_sdk.client.config import ClientConfig

__version__ = version("unifiedui-sdk")

__all__ = ["ClientConfig", "UnifiedUIClient", "__version__"]
