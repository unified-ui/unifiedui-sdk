"""Tests for client configuration."""

from __future__ import annotations

import pytest

from unifiedui_sdk.client.config import DEFAULT_BASE_PATH, DEFAULT_TIMEOUT, ClientConfig


class TestClientConfigValidation:
    """Tests for ClientConfig validation."""

    def test_valid_config_with_bearer_token(self) -> None:
        config = ClientConfig(base_url="https://api.example.com", tenant_id="t-1", bearer_token="tok")
        assert config.base_url == "https://api.example.com"
        assert config.tenant_id == "t-1"
        assert config.bearer_token == "tok"

    def test_valid_config_with_api_key(self) -> None:
        config = ClientConfig(base_url="https://api.example.com", tenant_id="t-1", api_key="key-123")
        assert config.api_key == "key-123"

    def test_valid_config_with_both_auth(self) -> None:
        config = ClientConfig(
            base_url="https://api.example.com",
            tenant_id="t-1",
            bearer_token="tok",
            api_key="key",
        )
        assert config.bearer_token == "tok"
        assert config.api_key == "key"

    def test_missing_base_url_raises(self) -> None:
        with pytest.raises(ValueError, match="base_url"):
            ClientConfig(base_url="", tenant_id="t-1", bearer_token="tok")

    def test_missing_tenant_id_raises(self) -> None:
        with pytest.raises(ValueError, match="tenant_id"):
            ClientConfig(base_url="https://api.example.com", tenant_id="", bearer_token="tok")

    def test_no_auth_raises(self) -> None:
        with pytest.raises(ValueError, match="bearer_token or api_key"):
            ClientConfig(base_url="https://api.example.com", tenant_id="t-1")

    def test_defaults(self) -> None:
        config = ClientConfig(base_url="https://api.example.com", tenant_id="t-1", bearer_token="tok")
        assert config.timeout == DEFAULT_TIMEOUT
        assert config.base_path == DEFAULT_BASE_PATH
        assert config.default_headers == {}


class TestClientConfigAuthHeaders:
    """Tests for ClientConfig.auth_headers property."""

    def test_bearer_only(self) -> None:
        config = ClientConfig(base_url="https://api.example.com", tenant_id="t-1", bearer_token="my-token")
        headers = config.auth_headers
        assert headers == {"Authorization": "Bearer my-token"}

    def test_api_key_only(self) -> None:
        config = ClientConfig(base_url="https://api.example.com", tenant_id="t-1", api_key="my-key")
        headers = config.auth_headers
        assert headers == {"X-Unified-UI-Autonomous-Agent-API-Key": "my-key"}

    def test_both_auth_methods(self) -> None:
        config = ClientConfig(
            base_url="https://api.example.com",
            tenant_id="t-1",
            bearer_token="tok",
            api_key="key",
        )
        headers = config.auth_headers
        assert headers["Authorization"] == "Bearer tok"
        assert headers["X-Unified-UI-Autonomous-Agent-API-Key"] == "key"


class TestClientConfigBuildUrl:
    """Tests for ClientConfig.build_url."""

    def test_builds_full_url(self) -> None:
        config = ClientConfig(base_url="https://api.example.com", tenant_id="t-1", bearer_token="tok")
        url = config.build_url("/tenants/t-1/traces")
        assert url == "https://api.example.com/api/v1/agent-service/tenants/t-1/traces"

    def test_strips_trailing_slash(self) -> None:
        config = ClientConfig(base_url="https://api.example.com/", tenant_id="t-1", bearer_token="tok")
        url = config.build_url("/tenants/t-1/traces")
        assert url == "https://api.example.com/api/v1/agent-service/tenants/t-1/traces"

    def test_custom_base_path(self) -> None:
        config = ClientConfig(
            base_url="https://api.example.com",
            tenant_id="t-1",
            bearer_token="tok",
            base_path="/custom/v2",
        )
        url = config.build_url("/test")
        assert url == "https://api.example.com/custom/v2/test"

    def test_frozen_immutability(self) -> None:
        config = ClientConfig(base_url="https://api.example.com", tenant_id="t-1", bearer_token="tok")
        with pytest.raises(AttributeError):
            config.base_url = "https://other.com"  # type: ignore[misc]
