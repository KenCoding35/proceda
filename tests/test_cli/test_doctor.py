"""Tests for the doctor CLI command."""

from __future__ import annotations

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
