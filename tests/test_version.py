"""Smoke tests for package metadata."""

import unifiedui_sdk


def test_version_is_string() -> None:
    """Version should be a non-empty string."""
    assert isinstance(unifiedui_sdk.__version__, str)
    assert len(unifiedui_sdk.__version__) > 0


def test_version_format() -> None:
    """Version should follow semver-like pattern (x.y.z)."""
    parts = unifiedui_sdk.__version__.split(".")
    assert len(parts) >= 2
    assert all(part.isdigit() for part in parts[:3])
