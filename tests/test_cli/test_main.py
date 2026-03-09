"""Tests for the CLI main entry point."""

from __future__ import annotations

from typer.testing import CliRunner

from proceda.cli.main import app

runner = CliRunner()


class TestCLIMain:
    def test_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "proceda" in result.output.lower() or "Proceda" in result.output

    def test_run_help(self) -> None:
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "SKILL.md" in result.output or "path" in result.output.lower()

    def test_lint_help(self) -> None:
        result = runner.invoke(app, ["lint", "--help"])
        assert result.exit_code == 0

    def test_replay_help(self) -> None:
        result = runner.invoke(app, ["replay", "--help"])
        assert result.exit_code == 0

    def test_doctor_help(self) -> None:
        result = runner.invoke(app, ["doctor", "--help"])
        assert result.exit_code == 0
