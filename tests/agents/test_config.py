"""Tests for agent configuration models."""

from __future__ import annotations

import pytest

from unifiedui_sdk.agents.config import (
    MCPTransport,
    MultiAgentConfig,
    ReActAgentConfig,
    ToolAuthType,
    ToolConfig,
    ToolType,
)


class TestToolType:
    """Tests for ToolType enum."""

    def test_values(self) -> None:
        assert ToolType.MCP_SERVER == "MCP_SERVER"
        assert ToolType.OPENAPI_DEFINITION == "OPENAPI_DEFINITION"

    def test_count(self) -> None:
        assert len(ToolType) == 2


class TestToolAuthType:
    """Tests for ToolAuthType enum."""

    def test_values(self) -> None:
        assert ToolAuthType.NONE == "none"
        assert ToolAuthType.BEARER == "bearer"
        assert ToolAuthType.API_KEY_HEADER == "api_key_header"
        assert ToolAuthType.API_KEY_QUERY == "api_key_query"
        assert ToolAuthType.BASIC == "basic"

    def test_count(self) -> None:
        assert len(ToolAuthType) == 5


class TestMCPTransport:
    """Tests for MCPTransport enum."""

    def test_values(self) -> None:
        assert MCPTransport.SSE == "sse"
        assert MCPTransport.STREAMABLE_HTTP == "streamable_http"
        assert MCPTransport.STDIO == "stdio"

    def test_count(self) -> None:
        assert len(MCPTransport) == 3


class TestToolConfig:
    """Tests for ToolConfig model."""

    def test_minimal(self) -> None:
        cfg = ToolConfig(type=ToolType.MCP_SERVER)
        assert cfg.type == ToolType.MCP_SERVER
        assert cfg.name == ""
        assert cfg.config == {}
        assert cfg.credential is None
        assert cfg.auth_type == ToolAuthType.NONE

    def test_full(self) -> None:
        cfg = ToolConfig(
            name="My API",
            type=ToolType.OPENAPI_DEFINITION,
            config={"spec_url": "https://example.com/spec.json", "base_url": "https://api.example.com"},
            credential="my-key",
            auth_type=ToolAuthType.BEARER,
        )
        assert cfg.name == "My API"
        assert cfg.credential == "my-key"
        assert cfg.auth_type == ToolAuthType.BEARER
        assert cfg.config["spec_url"] == "https://example.com/spec.json"


class TestMultiAgentConfig:
    """Tests for MultiAgentConfig model."""

    def test_defaults(self) -> None:
        cfg = MultiAgentConfig()
        assert cfg.max_sub_agents == 5
        assert cfg.max_parallel_per_step == 3
        assert cfg.max_planning_iterations == 2
        assert cfg.sub_agent_max_iterations == 10
        assert cfg.sub_agent_max_execution_time_seconds == 60
        assert cfg.planning_model_id is None

    def test_custom_values(self) -> None:
        cfg = MultiAgentConfig(
            max_sub_agents=10,
            max_parallel_per_step=5,
            planning_model_id="gpt-4o",
        )
        assert cfg.max_sub_agents == 10
        assert cfg.max_parallel_per_step == 5
        assert cfg.planning_model_id == "gpt-4o"


class TestReActAgentConfig:
    """Tests for ReActAgentConfig model."""

    def test_defaults(self) -> None:
        cfg = ReActAgentConfig()
        assert cfg.system_prompt is None
        assert cfg.security_prompt is None
        assert cfg.tool_use_prompt is None
        assert cfg.response_prompt is None
        assert cfg.max_iterations == 15
        assert cfg.max_execution_time_seconds == 120
        assert cfg.temperature == pytest.approx(0.1)
        assert cfg.parallel_tool_calls is True
        assert cfg.multi_agent_enabled is False
        assert isinstance(cfg.multi_agent, MultiAgentConfig)

    def test_full_config(self) -> None:
        cfg = ReActAgentConfig(
            system_prompt="You are a helpful assistant.",
            security_prompt="Do not reveal secrets.",
            tool_use_prompt="Use tools wisely.",
            response_prompt="Respond in markdown.",
            max_iterations=20,
            temperature=0.7,
            multi_agent_enabled=True,
            multi_agent=MultiAgentConfig(max_sub_agents=8),
        )
        assert cfg.system_prompt == "You are a helpful assistant."
        assert cfg.security_prompt == "Do not reveal secrets."
        assert cfg.multi_agent_enabled is True
        assert cfg.multi_agent.max_sub_agents == 8

    def test_model_dump(self) -> None:
        cfg = ReActAgentConfig(system_prompt="test")
        dumped = cfg.model_dump()
        assert dumped["system_prompt"] == "test"
        assert "multi_agent" in dumped
        assert dumped["multi_agent"]["max_sub_agents"] == 5

    def test_multi_agent_defaults_nested(self) -> None:
        cfg = ReActAgentConfig()
        assert cfg.multi_agent.max_sub_agents == 5
        assert cfg.multi_agent.sub_agent_max_iterations == 10
