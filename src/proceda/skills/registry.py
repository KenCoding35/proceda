"""ABOUTME: Discovers and caches skills from configured search paths.
ABOUTME: Recursively scans directories for SKILL.md files and provides lookup by name."""

from __future__ import annotations

from pathlib import Path

from proceda.exceptions import SkillLoadError
from proceda.skill import Skill
from proceda.skills.loader import SKILL_FILENAME, load_skill


class SkillRegistry:
    """Discovers and caches skills from configured search paths."""

    def __init__(self, search_paths: list[Path] | None = None) -> None:
        self._search_paths = search_paths or [Path(".")]
        self._cache: dict[str, Skill] = {}

    def discover(self) -> list[Skill]:
        """Find all skills in search paths."""
        skills: list[Skill] = []
        for base in self._search_paths:
            if not base.exists():
                continue
            for skill_file in base.rglob(SKILL_FILENAME):
                try:
                    skill = load_skill(skill_file)
                    skills.append(skill)
                    self._cache[skill.name] = skill
                except Exception:
                    continue
        return skills

    def get(self, name: str) -> Skill:
        """Get a skill by name from cache."""
        if name not in self._cache:
            self.discover()
        if name not in self._cache:
            raise SkillLoadError(f"Skill '{name}' not found in search paths")
        return self._cache[name]
