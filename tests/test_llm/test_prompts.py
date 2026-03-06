"""Tests for prompt construction."""

from __future__ import annotations

from skillrunner.llm.prompts import build_step_prompt, build_system_prompt
from skillrunner.skill import SkillStep, StepMarker


class TestBuildSystemPrompt:
    def test_includes_skill_name(self, sample_skill) -> None:
        prompt = build_system_prompt(sample_skill)
        assert "test-skill" in prompt

    def test_includes_description(self, sample_skill) -> None:
        prompt = build_system_prompt(sample_skill)
        assert "A test skill for unit tests" in prompt

    def test_includes_step_definitions(self, sample_skill) -> None:
        prompt = build_system_prompt(sample_skill)
        assert "Step 1: First step" in prompt
        assert "Step 2: Second step with approval" in prompt

    def test_includes_required_tools(self, sample_skill) -> None:
        prompt = build_system_prompt(sample_skill)
        assert "test__tool_a" in prompt
        assert "test__tool_b" in prompt

    def test_includes_variables(self, sample_skill) -> None:
        prompt = build_system_prompt(sample_skill, variables={"ticket_id": "INC-123"})
        assert "ticket_id" in prompt
        assert "INC-123" in prompt

    def test_includes_control_tool_instructions(self, sample_skill) -> None:
        prompt = build_system_prompt(sample_skill)
        assert "complete_step" in prompt
        assert "request_clarification" in prompt


class TestBuildStepPrompt:
    def test_step_prompt(self) -> None:
        step = SkillStep(index=1, title="Test Step", content="Do the thing.")
        prompt = build_step_prompt(step)
        assert "Step 1: Test Step" in prompt
        assert "Do the thing." in prompt
        assert "complete_step" in prompt

    def test_step_prompt_with_markers(self) -> None:
        step = SkillStep(
            index=2,
            title="Approval Step",
            content="Content.",
            markers=[StepMarker.APPROVAL_REQUIRED],
        )
        prompt = build_step_prompt(step)
        assert "APPROVAL REQUIRED" in prompt
