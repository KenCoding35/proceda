"""ABOUTME: Generates human-readable summaries of completed skill runs.
ABOUTME: Formats step outcomes, duration, and approval counts into a text report."""

from __future__ import annotations

from proceda.session import RunSession, RunStatus
from proceda.skill import Skill


def generate_run_summary(session: RunSession, skill: Skill) -> str:
    """Generate a human-readable summary of a completed run."""
    lines: list[str] = []

    status_emoji = {
        RunStatus.COMPLETED: "Completed",
        RunStatus.FAILED: "Failed",
        RunStatus.CANCELLED: "Cancelled",
    }.get(session.status, str(session.status.value))

    lines.append(f"Run {session.id}: {status_emoji}")
    lines.append(f"Skill: {skill.name}")
    lines.append(f"Steps completed: {len(session.completed_steps)}/{skill.step_count}")

    if session.skipped_steps:
        lines.append(f"Steps skipped: {len(session.skipped_steps)}")

    if session.started_at and session.completed_at:
        duration = session.completed_at - session.started_at
        lines.append(f"Duration: {duration.total_seconds():.1f}s")

    if session.approval_records:
        lines.append(f"Approvals: {len(session.approval_records)}")

    # Summarize step outcomes
    lines.append("")
    lines.append("Step details:")
    for step in skill.steps:
        if step.index in session.completed_steps:
            lines.append(f"  Step {step.index}: {step.title} - completed")
        elif step.index in session.skipped_steps:
            lines.append(f"  Step {step.index}: {step.title} - skipped")
        elif session.status == RunStatus.FAILED and step.index == session.current_step:
            lines.append(f"  Step {step.index}: {step.title} - failed")
        else:
            lines.append(f"  Step {step.index}: {step.title} - not reached")

    return "\n".join(lines)
