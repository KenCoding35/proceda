"""Tests for the SKILL.md parser."""

from __future__ import annotations

import pytest

from skillrunner.exceptions import SkillParseError
from skillrunner.skills.parser import lint_skill, parse_skill
from tests.conftest import (
    MALFORMED_SKILL_DUPLICATE_STEPS,
    MALFORMED_SKILL_NO_FRONTMATTER,
    MALFORMED_SKILL_NO_NAME,
    MALFORMED_SKILL_NO_STEPS,
    MALFORMED_SKILL_NONSEQUENTIAL,
    MINIMAL_SKILL_CONTENT,
    SAMPLE_SKILL_CONTENT,
)


class TestParseSkill:
    def test_parse_basic_skill(self) -> None:
        skill = parse_skill(SAMPLE_SKILL_CONTENT)
        assert skill.name == "test-skill"
        assert skill.description == "A test skill for unit tests"
        assert skill.step_count == 4
        assert skill.required_tools == ["test__tool_a", "test__tool_b"]

    def test_parse_step_titles(self) -> None:
        skill = parse_skill(SAMPLE_SKILL_CONTENT)
        assert skill.step_titles() == [
            "First step",
            "Second step with approval",
            "Third step with pre-approval",
            "Optional step",
        ]

    def test_parse_step_indices(self) -> None:
        skill = parse_skill(SAMPLE_SKILL_CONTENT)
        for i, step in enumerate(skill.steps, 1):
            assert step.index == i

    def test_parse_approval_required_marker(self) -> None:
        skill = parse_skill(SAMPLE_SKILL_CONTENT)
        step2 = skill.get_step(2)
        assert step2.requires_post_approval
        assert not step2.requires_pre_approval

    def test_parse_pre_approval_required_marker(self) -> None:
        skill = parse_skill(SAMPLE_SKILL_CONTENT)
        step3 = skill.get_step(3)
        assert step3.requires_pre_approval
        assert not step3.requires_post_approval

    def test_parse_optional_marker(self) -> None:
        skill = parse_skill(SAMPLE_SKILL_CONTENT)
        step4 = skill.get_step(4)
        assert step4.is_optional

    def test_step_without_markers(self) -> None:
        skill = parse_skill(SAMPLE_SKILL_CONTENT)
        step1 = skill.get_step(1)
        assert step1.markers == []
        assert not step1.requires_pre_approval
        assert not step1.requires_post_approval
        assert not step1.is_optional

    def test_parse_minimal_skill(self) -> None:
        skill = parse_skill(MINIMAL_SKILL_CONTENT)
        assert skill.name == "minimal-skill"
        assert skill.step_count == 1
        assert skill.required_tools is None

    def test_parse_preserves_raw_content(self) -> None:
        skill = parse_skill(SAMPLE_SKILL_CONTENT)
        assert skill.raw_content == SAMPLE_SKILL_CONTENT

    def test_parse_generates_id(self) -> None:
        skill = parse_skill(SAMPLE_SKILL_CONTENT)
        assert skill.id
        assert len(skill.id) == 16

    def test_same_content_same_id(self) -> None:
        skill1 = parse_skill(SAMPLE_SKILL_CONTENT)
        skill2 = parse_skill(SAMPLE_SKILL_CONTENT)
        assert skill1.id == skill2.id

    def test_get_step_invalid_index(self) -> None:
        skill = parse_skill(SAMPLE_SKILL_CONTENT)
        with pytest.raises(ValueError, match="Step 99 not found"):
            skill.get_step(99)

    def test_parse_with_path(self, tmp_path) -> None:
        p = tmp_path / "test.md"
        p.write_text(SAMPLE_SKILL_CONTENT)
        skill = parse_skill(SAMPLE_SKILL_CONTENT, path=p)
        assert skill.path == p


class TestParseSkillErrors:
    def test_no_frontmatter(self) -> None:
        with pytest.raises(SkillParseError, match="Missing YAML frontmatter"):
            parse_skill(MALFORMED_SKILL_NO_FRONTMATTER)

    def test_no_name(self) -> None:
        with pytest.raises(SkillParseError, match="must include 'name'"):
            parse_skill(MALFORMED_SKILL_NO_NAME)

    def test_no_steps(self) -> None:
        with pytest.raises(SkillParseError, match="No steps found"):
            parse_skill(MALFORMED_SKILL_NO_STEPS)

    def test_duplicate_steps(self) -> None:
        with pytest.raises(SkillParseError, match="Duplicate step number"):
            parse_skill(MALFORMED_SKILL_DUPLICATE_STEPS)

    def test_nonsequential_steps(self) -> None:
        with pytest.raises(SkillParseError, match="sequential"):
            parse_skill(MALFORMED_SKILL_NONSEQUENTIAL)

    def test_no_description(self) -> None:
        content = "---\nname: test\n---\n\n### Step 1: Step\nContent."
        with pytest.raises(SkillParseError, match="must include 'description'"):
            parse_skill(content)

    def test_invalid_required_tools_type(self) -> None:
        content = (
            "---\nname: test\ndescription: test\n"
            "required_tools: not-a-list\n---\n\n### Step 1: Step\nContent."
        )
        with pytest.raises(SkillParseError, match="must be a list"):
            parse_skill(content)


class TestLintSkill:
    def test_lint_valid_skill(self) -> None:
        result = lint_skill(SAMPLE_SKILL_CONTENT)
        assert result.ok
        assert result.skill is not None

    def test_lint_missing_required_tools(self) -> None:
        result = lint_skill(MINIMAL_SKILL_CONTENT)
        assert result.ok
        assert result.has_warnings
        assert any("required_tools" in w.message for w in result.warnings)

    def test_lint_malformed_skill(self) -> None:
        result = lint_skill(MALFORMED_SKILL_NO_FRONTMATTER)
        assert not result.ok
        assert len(result.errors) > 0

    def test_lint_empty_step_body(self) -> None:
        content = (
            "---\nname: test\ndescription: test\nrequired_tools:\n  - tool\n---\n\n"
            "### Step 1: Empty\n\n### Step 2: Not empty\nContent here."
        )
        result = lint_skill(content)
        assert result.ok
        assert any("no body content" in w.message for w in result.warnings)
