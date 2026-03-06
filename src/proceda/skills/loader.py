"""Skill loader: resolves file/directory paths and loads SKILL.md content."""

from __future__ import annotations

import asyncio
from pathlib import Path

from proceda.config import LLMConfig
from proceda.exceptions import SkillLoadError
from proceda.skill import Skill
from proceda.skills.parser import parse_skill

SKILL_FILENAME = "SKILL.md"


def load_skill(path: str | Path, llm_config: LLMConfig | None = None) -> Skill:
    """Load a skill from a file path or directory path.

    If path is a directory, looks for SKILL.md inside it.
    If path is a file, loads it directly.

    When llm_config is provided and the content lacks valid step headings,
    attempts LLM-based auto-structuring before parsing.
    """
    resolved = Path(path).resolve()

    if resolved.is_dir():
        skill_file = resolved / SKILL_FILENAME
        if not skill_file.exists():
            raise SkillLoadError(f"No {SKILL_FILENAME} found in directory: {resolved}")
        return _load_file(skill_file, llm_config)

    if resolved.is_file():
        return _load_file(resolved, llm_config)

    raise SkillLoadError(f"Path does not exist: {resolved}")


def _load_file(path: Path, llm_config: LLMConfig | None = None) -> Skill:
    """Load and parse a single skill file."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise SkillLoadError(f"Cannot read {path}: {e}") from e

    if llm_config is not None:
        from proceda.skills.structurer import auto_structure

        content = asyncio.run(auto_structure(content, llm_config))

    return parse_skill(content, path=path)
