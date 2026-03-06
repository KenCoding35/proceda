"""Tests for the skill loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from skillrunner.exceptions import SkillLoadError
from skillrunner.skills.loader import load_skill


class TestLoadSkill:
    def test_load_from_directory(self, tmp_skill_dir: Path) -> None:
        skill = load_skill(tmp_skill_dir)
        assert skill.name == "test-skill"
        assert skill.path is not None

    def test_load_from_file(self, tmp_skill_file: Path) -> None:
        skill = load_skill(tmp_skill_file)
        assert skill.name == "test-skill"

    def test_load_missing_path(self, tmp_path: Path) -> None:
        with pytest.raises(SkillLoadError, match="does not exist"):
            load_skill(tmp_path / "nonexistent")

    def test_load_directory_without_skill_md(self, tmp_path: Path) -> None:
        with pytest.raises(SkillLoadError, match="No SKILL.md found"):
            load_skill(tmp_path)

    def test_load_from_string_path(self, tmp_skill_dir: Path) -> None:
        skill = load_skill(str(tmp_skill_dir))
        assert skill.name == "test-skill"
