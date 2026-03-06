"""Skill loader: resolves file/directory paths and loads SKILL.md content."""

from __future__ import annotations

from pathlib import Path

from skillrunner.exceptions import SkillLoadError
from skillrunner.skill import Skill
from skillrunner.skills.parser import parse_skill

SKILL_FILENAME = "SKILL.md"


def load_skill(path: str | Path) -> Skill:
    """Load a skill from a file path or directory path.

    If path is a directory, looks for SKILL.md inside it.
    If path is a file, loads it directly.
    """
    resolved = Path(path).resolve()

    if resolved.is_dir():
        skill_file = resolved / SKILL_FILENAME
        if not skill_file.exists():
            raise SkillLoadError(f"No {SKILL_FILENAME} found in directory: {resolved}")
        return _load_file(skill_file)

    if resolved.is_file():
        return _load_file(resolved)

    raise SkillLoadError(f"Path does not exist: {resolved}")


def _load_file(path: Path) -> Skill:
    """Load and parse a single skill file."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise SkillLoadError(f"Cannot read {path}: {e}") from e

    return parse_skill(content, path=path)
