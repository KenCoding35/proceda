"""ABOUTME: Tests for the doctor CLI command covering health checks and output format.
ABOUTME: Validates that doctor checks Python version, packages, config, and API keys.
"""

from __future__ import annotations

import sys

from typer.testing import CliRunner

from proceda.cli.main import app

runner = CliRunner()


class TestDoctorCommand:
    def test_doctor_runs(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "Python version" in result.output
        assert "Proceda Doctor" in result.output

    def test_doctor_checks_python_version(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "Python version" in result.output
        assert "OK" in result.output

    def test_doctor_shows_current_python_version(self) -> None:
        result = runner.invoke(app, ["doctor"])
        expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert expected in result.output

    def test_doctor_checks_required_packages(self) -> None:
        result = runner.invoke(app, ["doctor"])
        for pkg in ["litellm", "typer", "rich", "yaml", "httpx"]:
            assert pkg in result.output

    def test_doctor_shows_config_status(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "Config file" in result.output

    def test_doctor_shows_llm_api_key_status(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "LLM API key" in result.output

    def test_doctor_shows_run_directory_status(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "Run directory" in result.output

    def test_doctor_shows_mcp_apps_status(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "MCP apps" in result.output or "App:" in result.output

    def test_doctor_output_is_table_format(self) -> None:
        """Doctor output should contain the table column headers."""
        result = runner.invoke(app, ["doctor"])
        assert "Check" in result.output
        assert "Status" in result.output
        assert "Detail" in result.output

    def test_doctor_ends_with_summary(self) -> None:
        result = runner.invoke(app, ["doctor"])
        output_lower = result.output.lower()
        assert "all checks passed" in output_lower or "some checks failed" in output_lower
