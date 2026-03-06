"""Tests for configuration loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from skillrunner.config import SkillRunnerConfig, _expand_env
from skillrunner.exceptions import ConfigError


class TestExpandEnv:
    def test_expand_set_variable(self) -> None:
        os.environ["TEST_VAR_XYZ"] = "hello"
        try:
            assert _expand_env("${TEST_VAR_XYZ}") == "hello"
        finally:
            del os.environ["TEST_VAR_XYZ"]

    def test_expand_with_default(self) -> None:
        result = _expand_env("${UNSET_VAR_12345:-fallback}")
        assert result == "fallback"

    def test_expand_unset_no_default(self) -> None:
        result = _expand_env("${UNSET_VAR_99999}")
        assert result == "${UNSET_VAR_99999}"

    def test_no_expansion_needed(self) -> None:
        assert _expand_env("plain text") == "plain text"


class TestSkillRunnerConfig:
    def test_default_config(self) -> None:
        config = SkillRunnerConfig()
        assert config.llm.model == "anthropic/claude-sonnet-4-20250514"
        assert config.llm.temperature == 0.7
        assert config.apps == []
        assert config.security.tool_denylist == []

    def test_from_dict(self) -> None:
        data = {
            "llm": {"model": "gpt-4", "temperature": 0.5},
            "security": {"tool_denylist": ["bad__*"]},
        }
        config = SkillRunnerConfig.from_dict(data)
        assert config.llm.model == "gpt-4"
        assert config.llm.temperature == 0.5
        assert config.security.tool_denylist == ["bad__*"]

    def test_from_dict_with_apps(self) -> None:
        data = {
            "apps": [
                {
                    "name": "test",
                    "description": "Test app",
                    "transport": "stdio",
                    "command": ["python", "-m", "test"],
                },
                {
                    "name": "http_app",
                    "description": "HTTP app",
                    "transport": "http",
                    "url": "http://localhost:8000",
                },
            ]
        }
        config = SkillRunnerConfig.from_dict(data)
        assert len(config.apps) == 2
        assert config.apps[0].name == "test"
        assert config.apps[0].transport == "stdio"
        assert config.apps[1].transport == "http"

    def test_load_from_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "skillrunner.yaml"
        config_file.write_text("llm:\n  model: test-model\n  temperature: 0.3\n")
        config = SkillRunnerConfig.load(str(config_file))
        assert config.llm.model == "test-model"
        assert config.llm.temperature == 0.3

    def test_load_missing_file(self) -> None:
        with pytest.raises(ConfigError, match="not found"):
            SkillRunnerConfig.load("/nonexistent/path.yaml")

    def test_load_defaults_when_no_file(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        config = SkillRunnerConfig.load()
        assert config.llm.model == "anthropic/claude-sonnet-4-20250514"

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "skillrunner.yaml"
        config_file.write_text("{{{{invalid yaml")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            SkillRunnerConfig.load(str(config_file))

    def test_dev_config(self) -> None:
        data = {"dev": {"show_reasoning": False, "log_mcp": False}}
        config = SkillRunnerConfig.from_dict(data)
        assert config.dev.show_reasoning is False
        assert config.dev.log_mcp is False

    def test_logging_config(self) -> None:
        data = {"logging": {"run_dir": "/tmp/runs", "redact_secrets": False}}
        config = SkillRunnerConfig.from_dict(data)
        assert config.logging.run_dir == "/tmp/runs"
        assert config.logging.redact_secrets is False
