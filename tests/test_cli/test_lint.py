"""Tests for the lint CLI command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from proceda.cli.main import app
from tests.conftest import MALFORMED_SKILL_NO_FRONTMATTER, SAMPLE_SKILL_CONTENT

runner = CliRunner()


class TestLintCommand:
    def test_lint_valid_skill_file(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(SAMPLE_SKILL_CONTENT)
        result = runner.invoke(app, ["lint", str(skill_file)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "test-skill" in result.output

    def test_lint_valid_skill_directory(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(SAMPLE_SKILL_CONTENT)
        result = runner.invoke(app, ["lint", str(tmp_path)])
        assert result.exit_code == 0

    def test_lint_invalid_skill(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(MALFORMED_SKILL_NO_FRONTMATTER)
        result = runner.invoke(app, ["lint", str(skill_file)])
        assert result.exit_code == 2

    def test_lint_nonexistent_path(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(tmp_path / "nonexistent")])
        assert result.exit_code == 2

    def test_lint_directory_without_skill(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(tmp_path)])
        assert result.exit_code == 2
