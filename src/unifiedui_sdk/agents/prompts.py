"""Prompt builder — assembles system prompts from ReACT agent configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unifiedui_sdk.agents.config import ReActAgentConfig


def build_system_prompt(config: ReActAgentConfig) -> str:
    """Build a composite system prompt from the agent configuration sections.

    Combines system_prompt, security_prompt, tool_use_prompt, and response_prompt
    into a structured XML-tagged prompt.

    Args:
        config: The agent configuration containing prompt sections.

    Returns:
        Combined system prompt string.
    """
    sections: list[str] = []

    if config.system_prompt:
        sections.append(f"<instructions>\n{config.system_prompt}\n</instructions>")
    if config.security_prompt:
        sections.append(f"<security>\n{config.security_prompt}\n</security>")
    if config.tool_use_prompt:
        sections.append(f"<tool_use>\n{config.tool_use_prompt}\n</tool_use>")
    if config.response_prompt:
        sections.append(f"<response_format>\n{config.response_prompt}\n</response_format>")

    return "\n\n".join(sections) if sections else "You are a helpful assistant."
