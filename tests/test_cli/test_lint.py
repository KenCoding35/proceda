"""ABOUTME: Tests for the lint CLI command covering valid, invalid, and edge-case skill files.
ABOUTME: Exercises error messages, warning output, and exit codes.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from proceda.cli.main import app
from tests.conftest import (
    MALFORMED_SKILL_NO_FRONTMATTER,
    MALFORMED_SKILL_NO_NAME,
    MALFORMED_SKILL_NO_STEPS,
    SAMPLE_SKILL_CONTENT,
)

runner = CliRunner()


class TestLintCommand:
    def test_lint_valid_skill_file(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(SAMPLE_SKILL_CONTENT)
        result = runner.invoke(app, ["lint", str(skill_file)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "test-skill" in result.output

    def test_lint_valid_skill_reports_step_count(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(SAMPLE_SKILL_CONTENT)
        result = runner.invoke(app, ["lint", str(skill_file)])
        assert result.exit_code == 0
        assert "Steps:" in result.output

    def test_lint_valid_skill_reports_required_tools(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(SAMPLE_SKILL_CONTENT)
        result = runner.invoke(app, ["lint", str(skill_file)])
        assert result.exit_code == 0
        assert "Required tools:" in result.output
        assert "test__tool_a" in result.output

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

    def test_lint_invalid_skill_shows_error(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(MALFORMED_SKILL_NO_FRONTMATTER)
        result = runner.invoke(app, ["lint", str(skill_file)])
        assert result.exit_code == 2
        assert "ERROR" in result.output

    def test_lint_missing_name_produces_error(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(MALFORMED_SKILL_NO_NAME)
        result = runner.invoke(app, ["lint", str(skill_file)])
        assert result.exit_code == 2
        assert "ERROR" in result.output

    def test_lint_no_steps_produces_error(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(MALFORMED_SKILL_NO_STEPS)
        result = runner.invoke(app, ["lint", str(skill_file)])
        assert result.exit_code == 2
        assert "ERROR" in result.output

    def test_lint_nonexistent_path(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(tmp_path / "nonexistent")])
        assert result.exit_code == 2

    def test_lint_nonexistent_path_shows_message(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(tmp_path / "nonexistent")])
        assert result.exit_code == 2
        assert "does not exist" in result.output.lower() or "not found" in result.output.lower()

    def test_lint_directory_without_skill(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(tmp_path)])
        assert result.exit_code == 2

    def test_lint_many_steps_produces_warning(self, tmp_path: Path) -> None:
        """A skill with >20 steps should produce a warning about breaking into smaller skills."""
        steps = "\n\n".join(f"### Step {i}: Step number {i}\nDo thing {i}." for i in range(1, 23))
        frontmatter = (
            "---\nname: big-skill\ndescription: Many steps\n"
            "required_tools:\n  - some__tool\n---\n\n"
        )
        content = f"{frontmatter}{steps}\n"
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(content)
        result = runner.invoke(app, ["lint", str(skill_file)])
        assert result.exit_code == 0
        assert "WARNING" in result.output
        assert "breaking" in result.output.lower() or "smaller" in result.output.lower()

    def test_lint_valid_with_warnings_shows_count(self, tmp_path: Path) -> None:
        """A valid skill with warnings should show the warning count."""
        content = (
            "---\nname: no-tools\ndescription: No tools declared\n"
            "---\n\n### Step 1: Only step\nDo something.\n"
        )
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(content)
        result = runner.invoke(app, ["lint", str(skill_file)])
        assert result.exit_code == 0
        assert "warning" in result.output.lower()
