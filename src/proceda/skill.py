"""ABOUTME: Data models for parsed SKILL.md files.
ABOUTME: Defines Skill, SkillStep, and StepMarker (approval, pre-approval, optional).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path


class StepMarker(enum.Enum):
    """Markers that modify step behavior."""

    APPROVAL_REQUIRED = "APPROVAL REQUIRED"
    PRE_APPROVAL_REQUIRED = "PRE-APPROVAL REQUIRED"
    OPTIONAL = "OPTIONAL"


@dataclass(frozen=True)
class SkillStep:
    """A single step within a skill."""

    index: int
    title: str
    content: str
    markers: list[StepMarker] = field(default_factory=list)

    @property
    def requires_pre_approval(self) -> bool:
        return StepMarker.PRE_APPROVAL_REQUIRED in self.markers

    @property
    def requires_post_approval(self) -> bool:
        return StepMarker.APPROVAL_REQUIRED in self.markers

    @property
    def is_optional(self) -> bool:
        return StepMarker.OPTIONAL in self.markers


@dataclass(frozen=True)
class Skill:
    """A parsed skill definition from a SKILL.md file."""

    id: str
    name: str
    description: str
    steps: list[SkillStep]
    raw_content: str
    path: Path | None = None
    source_url: str | None = None
    required_tools: list[str] | None = None

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def get_step(self, index: int) -> SkillStep:
        """Get a step by its index (1-based)."""
        for step in self.steps:
            if step.index == index:
                return step
        raise ValueError(f"Step {index} not found in skill '{self.name}'")

    def step_titles(self) -> list[str]:
        return [step.title for step in self.steps]
