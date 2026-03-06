"""Prompt construction for LLM calls."""

from __future__ import annotations

from skillrunner.skill import Skill, SkillStep


def build_system_prompt(skill: Skill, variables: dict[str, str] | None = None) -> str:
    """Build the system prompt for a skill execution."""
    parts = [
        f"You are executing the skill: {skill.name}",
        f"Description: {skill.description}",
        "",
        "You must follow the steps in order. For each step:",
        "1. Read the step instructions carefully",
        "2. Use the available tools to accomplish the step's goals",
        "3. Call `complete_step` with a summary when the step is done",
        "4. If you need clarification, call `request_clarification`",
        "",
        "Important rules:",
        "- Complete one step at a time",
        "- Do not skip steps unless they are marked [OPTIONAL]",
        "- Do not proceed to the next step until you call `complete_step`",
        "- If a step is marked [APPROVAL REQUIRED] or [PRE-APPROVAL REQUIRED], "
        "the system will handle approval automatically",
    ]

    if variables:
        parts.append("")
        parts.append("Variables provided:")
        for key, value in variables.items():
            parts.append(f"  {key} = {value}")

    if skill.required_tools:
        parts.append("")
        parts.append(f"Required tools: {', '.join(skill.required_tools)}")

    parts.append("")
    parts.append("Full skill definition:")
    parts.append("---")

    for step in skill.steps:
        markers = ""
        if step.markers:
            markers = " " + " ".join(f"[{m.value}]" for m in step.markers)
        parts.append(f"### Step {step.index}: {step.title}{markers}")
        parts.append(step.content)
        parts.append("")

    return "\n".join(parts)


def build_step_prompt(step: SkillStep) -> str:
    """Build a user-facing prompt for starting a specific step."""
    markers_text = ""
    if step.markers:
        markers_text = " (" + ", ".join(m.value for m in step.markers) + ")"

    return (
        f"Now execute Step {step.index}: {step.title}{markers_text}\n\n"
        f"{step.content}\n\n"
        f"When complete, call `complete_step` with a summary of what you did."
    )
