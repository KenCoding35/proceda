"""SKILL.md parser: converts markdown + YAML frontmatter into Skill models."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from proceda.exceptions import SkillParseError
from proceda.skill import Skill, SkillStep, StepMarker

_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_STEP_HEADING_PATTERN = re.compile(r"^###\s+Step\s+(\d+):\s+(.+)$", re.MULTILINE)
_MARKER_PATTERNS: dict[StepMarker, re.Pattern[str]] = {
    StepMarker.PRE_APPROVAL_REQUIRED: re.compile(r"\[PRE-APPROVAL\s+REQUIRED\]", re.IGNORECASE),
    StepMarker.APPROVAL_REQUIRED: re.compile(r"\[APPROVAL\s+REQUIRED\]", re.IGNORECASE),
    StepMarker.OPTIONAL: re.compile(r"\[OPTIONAL\]", re.IGNORECASE),
}


def _parse_frontmatter(content: str, path: str | None = None) -> tuple[dict, str]:
    """Extract YAML frontmatter and return (metadata, body)."""
    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        raise SkillParseError("Missing YAML frontmatter (must start with ---)", path=path)

    try:
        metadata = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        raise SkillParseError(f"Invalid YAML in frontmatter: {e}", path=path) from e

    body = content[match.end() :]
    return metadata, body


def _extract_markers(text: str) -> list[StepMarker]:
    """Find all step markers in a block of text."""
    markers = []
    for marker, pattern in _MARKER_PATTERNS.items():
        if pattern.search(text):
            # For APPROVAL_REQUIRED, skip if PRE-APPROVAL already matched
            if marker == StepMarker.APPROVAL_REQUIRED:
                if StepMarker.PRE_APPROVAL_REQUIRED in markers:
                    # Check there's a standalone [APPROVAL REQUIRED] not preceded by PRE-
                    cleaned = _MARKER_PATTERNS[StepMarker.PRE_APPROVAL_REQUIRED].sub("", text)
                    if not _MARKER_PATTERNS[StepMarker.APPROVAL_REQUIRED].search(cleaned):
                        continue
            markers.append(marker)
    return markers


def _parse_steps(body: str, path: str | None = None) -> list[SkillStep]:
    """Parse step headings and bodies from the markdown body."""
    matches = list(_STEP_HEADING_PATTERN.finditer(body))

    if not matches:
        raise SkillParseError("No steps found (expected '### Step N: Title' headings)", path=path)

    steps: list[SkillStep] = []
    seen_indices: set[int] = set()

    for i, match in enumerate(matches):
        index = int(match.group(1))
        title = match.group(2).strip()

        if index in seen_indices:
            raise SkillParseError(f"Duplicate step number: {index}", line=match.start(), path=path)
        seen_indices.add(index)

        # Extract body: from end of heading to start of next heading (or end of doc)
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        step_body = body[body_start:body_end].strip()

        markers = _extract_markers(step_body)

        steps.append(
            SkillStep(
                index=index,
                title=title,
                content=step_body,
                markers=markers,
            )
        )

    # Validate step numbering is sequential starting from 1
    indices = sorted(s.index for s in steps)
    expected = list(range(1, len(steps) + 1))
    if indices != expected:
        raise SkillParseError(
            f"Step numbering must be sequential starting from 1, got: {indices}",
            path=path,
        )

    return steps


def parse_skill(
    content: str,
    path: Path | None = None,
    source_url: str | None = None,
) -> Skill:
    """Parse a SKILL.md string into a Skill model."""
    path_str = str(path) if path else None
    metadata, body = _parse_frontmatter(content, path=path_str)

    name = metadata.get("name")
    if not name:
        raise SkillParseError("Frontmatter must include 'name'", path=path_str)

    description = metadata.get("description")
    if not description:
        raise SkillParseError("Frontmatter must include 'description'", path=path_str)

    required_tools = metadata.get("required_tools")
    if required_tools is not None and not isinstance(required_tools, list):
        raise SkillParseError("'required_tools' must be a list", path=path_str)

    steps = _parse_steps(body, path=path_str)

    skill_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    return Skill(
        id=skill_id,
        name=name,
        description=description,
        steps=steps,
        raw_content=content,
        path=path,
        source_url=source_url,
        required_tools=required_tools,
    )


@dataclass
class LintIssue:
    """A single lint warning or error."""

    level: str  # "error" or "warning"
    message: str
    line: int | None = None


@dataclass
class LintResult:
    """Results from linting a skill file."""

    errors: list[LintIssue] = field(default_factory=list)
    warnings: list[LintIssue] = field(default_factory=list)
    skill: Skill | None = None

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


def lint_skill(content: str, path: Path | None = None) -> LintResult:
    """Lint a SKILL.md file and return warnings and errors."""
    errors: list[LintIssue] = []
    warnings: list[LintIssue] = []
    # Try parsing - any parse error is a lint error
    try:
        skill = parse_skill(content, path=path)
    except SkillParseError as e:
        errors.append(LintIssue(level="error", message=str(e), line=e.line))
        return LintResult(errors=errors, warnings=warnings, skill=None)

    # Warnings
    if skill.required_tools is None:
        warnings.append(
            LintIssue(
                level="warning",
                message="No 'required_tools' declared; consider adding tool requirements",
            )
        )

    if skill.step_count > 20:
        warnings.append(
            LintIssue(
                level="warning",
                message=(
                    f"Skill has {skill.step_count} steps; consider breaking into smaller skills"
                ),
            )
        )

    if len(content) > 50000:
        warnings.append(
            LintIssue(
                level="warning",
                message=(
                    f"Skill file is {len(content)} bytes; large skills may impact LLM performance"
                ),
            )
        )

    # Check for steps without content
    for step in skill.steps:
        if not step.content.strip():
            warnings.append(
                LintIssue(
                    level="warning",
                    message=f"Step {step.index} ('{step.title}') has no body content",
                )
            )

    return LintResult(errors=errors, warnings=warnings, skill=skill)
