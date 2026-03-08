"""Agent configuration models — ReACT agent and multi-agent config."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ToolType(StrEnum):
    """Supported tool integration types."""

    MCP_SERVER = "MCP_SERVER"
    OPENAPI_DEFINITION = "OPENAPI_DEFINITION"


class ToolAuthType(StrEnum):
    """Authentication types for tool integrations."""

    NONE = "none"
    BEARER = "bearer"
    API_KEY_HEADER = "api_key_header"
    API_KEY_QUERY = "api_key_query"
    BASIC = "basic"


class MCPTransport(StrEnum):
    """MCP server transport types."""

    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"
    STDIO = "stdio"


class ToolConfig(BaseModel):
    """Configuration for a single tool integration.

    Attributes:
        name: Display name for the tool.
        type: Tool integration type (MCP_SERVER or OPENAPI_DEFINITION).
        config: Type-specific configuration dict.
        credential: Optional credential/API key for authentication.
        auth_type: Authentication type (bearer, api_key_header, etc.).
    """

    name: str = ""
    type: ToolType
    config: dict[str, object] = Field(default_factory=dict)
    credential: str | None = None
    auth_type: ToolAuthType = ToolAuthType.NONE


class MultiAgentConfig(BaseModel):
    """Configuration for multi-agent orchestration.

    Attributes:
        max_sub_agents: Maximum number of sub-agents in a plan.
        max_parallel_per_step: Maximum sub-agents running in parallel per step.
        max_planning_iterations: Maximum planner retries on invalid plans.
        sub_agent_max_iterations: Maximum ReACT iterations per sub-agent.
        sub_agent_max_execution_time_seconds: Timeout per sub-agent.
        planning_model_id: Optional model override for the planner.
    """

    max_sub_agents: int = 5
    max_parallel_per_step: int = 3
    max_planning_iterations: int = 2
    sub_agent_max_iterations: int = 10
    sub_agent_max_execution_time_seconds: int = 60
    planning_model_id: str | None = None


class ReActAgentConfig(BaseModel):
    """Configuration for a ReACT agent engine instance.

    Attributes:
        system_prompt: Main system instructions for the agent.
        security_prompt: Security guardrail instructions injected as system-level guard.
        tool_use_prompt: Instructions for how the agent should use tools.
        response_prompt: Instructions for response format and style.
        max_iterations: Maximum ReACT loop iterations (single-agent mode).
        max_execution_time_seconds: Overall timeout for the agent execution.
        temperature: LLM temperature for generation.
        parallel_tool_calls: Whether to allow parallel tool calls if supported.
        multi_agent_enabled: Enable multi-agent orchestration mode.
        multi_agent: Multi-agent-specific configuration.
    """

    system_prompt: str | None = None
    security_prompt: str | None = None
    tool_use_prompt: str | None = None
    response_prompt: str | None = None
    max_iterations: int = 15
    max_execution_time_seconds: int = 120
    temperature: float = 0.1
    parallel_tool_calls: bool = True
    multi_agent_enabled: bool = False
    multi_agent: MultiAgentConfig = Field(default_factory=MultiAgentConfig)
