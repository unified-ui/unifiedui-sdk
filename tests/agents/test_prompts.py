"""Tests for prompt builder."""

from __future__ import annotations

from unifiedui_sdk.agents.config import ReActAgentConfig
from unifiedui_sdk.agents.prompts import build_system_prompt


class TestBuildSystemPrompt:
    """Tests for build_system_prompt function."""

    def test_all_sections(self) -> None:
        config = ReActAgentConfig(
            system_prompt="Be helpful.",
            security_prompt="No secrets.",
            tool_use_prompt="Use tools carefully.",
            response_prompt="Respond in markdown.",
        )
        result = build_system_prompt(config)
        assert "<instructions>" in result
        assert "Be helpful." in result
        assert "<security>" in result
        assert "No secrets." in result
        assert "<tool_use>" in result
        assert "Use tools carefully." in result
        assert "<response_format>" in result
        assert "Respond in markdown." in result

    def test_only_system_prompt(self) -> None:
        config = ReActAgentConfig(system_prompt="Be helpful.")
        result = build_system_prompt(config)
        assert "<instructions>" in result
        assert "Be helpful." in result
        assert "<security>" not in result
        assert "<tool_use>" not in result
        assert "<response_format>" not in result

    def test_no_sections(self) -> None:
        config = ReActAgentConfig()
        result = build_system_prompt(config)
        assert result == "You are a helpful assistant."

    def test_system_and_security_only(self) -> None:
        config = ReActAgentConfig(
            system_prompt="Help me.",
            security_prompt="Stay safe.",
        )
        result = build_system_prompt(config)
        assert "<instructions>" in result
        assert "<security>" in result
        assert "<tool_use>" not in result
        assert "\n\n" in result

    def test_sections_separated_by_double_newline(self) -> None:
        config = ReActAgentConfig(
            system_prompt="A",
            security_prompt="B",
        )
        result = build_system_prompt(config)
        parts = result.split("\n\n")
        assert len(parts) == 2

    def test_xml_tags_properly_closed(self) -> None:
        config = ReActAgentConfig(
            system_prompt="test",
            security_prompt="test",
            tool_use_prompt="test",
            response_prompt="test",
        )
        result = build_system_prompt(config)
        assert result.count("<instructions>") == 1
        assert result.count("</instructions>") == 1
        assert result.count("<security>") == 1
        assert result.count("</security>") == 1
        assert result.count("<tool_use>") == 1
        assert result.count("</tool_use>") == 1
        assert result.count("<response_format>") == 1
        assert result.count("</response_format>") == 1
