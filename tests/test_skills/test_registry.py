"""ABOUTME: Tests for SkillRegistry discovery and caching.
ABOUTME: Validates skill discovery across search paths, caching, and error handling."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from proceda.exceptions import SkillLoadError
from proceda.skills.registry import SkillRegistry

VALID_SKILL = """\
---
name: {name}
description: A test skill
---

### Step 1: Do something
Content here.
"""


def _write_skill(directory: Path, name: str = "test-skill") -> Path:
    """Write a valid SKILL.md into directory and return the directory."""
    skill_file = directory / "SKILL.md"
    skill_file.write_text(VALID_SKILL.format(name=name))
    return directory


class TestDiscover:
    def test_finds_skill_in_search_path(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "my-skill")
        registry = SkillRegistry(search_paths=[tmp_path])
        skills = registry.discover()
        assert len(skills) == 1
        assert skills[0].name == "my-skill"

    def test_multiple_search_paths(self, tmp_path: Path) -> None:
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        _write_skill(dir_a, "skill-a")
        _write_skill(dir_b, "skill-b")

        registry = SkillRegistry(search_paths=[dir_a, dir_b])
        skills = registry.discover()
        names = {s.name for s in skills}
        assert names == {"skill-a", "skill-b"}

    def test_skips_nonexistent_paths(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        _write_skill(tmp_path, "real-skill")
        registry = SkillRegistry(search_paths=[missing, tmp_path])
        skills = registry.discover()
        assert len(skills) == 1
        assert skills[0].name == "real-skill"

    def test_skips_invalid_skill_and_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("not valid yaml frontmatter\n### no steps")

        good_dir = tmp_path / "good"
        good_dir.mkdir()
        _write_skill(good_dir, "good-skill")

        registry = SkillRegistry(search_paths=[bad_dir, good_dir])
        caplog.set_level(logging.WARNING)
        skills = registry.discover()

        assert len(skills) == 1
        assert skills[0].name == "good-skill"
        assert "Failed to load skill from" in caplog.text

    def test_caches_discovered_skills(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "cached-skill")
        registry = SkillRegistry(search_paths=[tmp_path])
        registry.discover()
        assert "cached-skill" in registry._cache
        assert registry._cache["cached-skill"].name == "cached-skill"

    def test_nested_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "level1" / "level2"
        nested.mkdir(parents=True)
        _write_skill(nested, "nested-skill")

        registry = SkillRegistry(search_paths=[tmp_path])
        skills = registry.discover()
        assert len(skills) == 1
        assert skills[0].name == "nested-skill"

    def test_empty_directory(self, tmp_path: Path) -> None:
        registry = SkillRegistry(search_paths=[tmp_path])
        skills = registry.discover()
        assert skills == []


class TestGet:
    def test_returns_cached_skill(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "my-skill")
        registry = SkillRegistry(search_paths=[tmp_path])
        registry.discover()
        skill = registry.get("my-skill")
        assert skill.name == "my-skill"

    def test_triggers_discover_if_not_cached(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "lazy-skill")
        registry = SkillRegistry(search_paths=[tmp_path])
        # No explicit discover() call
        skill = registry.get("lazy-skill")
        assert skill.name == "lazy-skill"

    def test_raises_for_missing_skill(self, tmp_path: Path) -> None:
        registry = SkillRegistry(search_paths=[tmp_path])
        with pytest.raises(SkillLoadError, match="not found in search paths"):
            registry.get("nonexistent")
