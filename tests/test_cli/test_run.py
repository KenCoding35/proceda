"""ABOUTME: Tests for the run CLI command covering argument validation and error paths.
ABOUTME: Tests missing files, invalid paths, and variable parsing without invoking the LLM.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from proceda.cli.main import app

runner = CliRunner()


class TestRunCommand:
    def test_run_missing_skill_file(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["run", str(tmp_path / "nonexistent" / "SKILL.md")])
        assert result.exit_code == 1
        assert "error" in result.output.lower()

    def test_run_invalid_path(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["run", str(tmp_path / "does-not-exist")])
        assert result.exit_code == 1

    def test_run_empty_directory(self, tmp_path: Path) -> None:
        """Running against an empty directory (no SKILL.md) should fail."""
        result = runner.invoke(app, ["run", str(tmp_path)])
        assert result.exit_code == 1

    def test_run_invalid_variable_format(self, tmp_path: Path) -> None:
        """Variables must be in key=value format."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\nname: test\ndescription: test\n---\n\n### Step 1: Do it\nContent.\n"
        )
        result = runner.invoke(app, ["run", str(skill_file), "--var", "badformat"])
        assert result.exit_code == 2
        assert "key=value" in result.output.lower()

    def test_run_no_arguments(self) -> None:
        """Running without any arguments should show an error or help."""
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0
