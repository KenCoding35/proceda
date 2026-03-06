"""Tests for summary generation."""

from __future__ import annotations

from proceda.internal.summary import generate_run_summary
from proceda.session import RunSession, RunStatus


class TestGenerateRunSummary:
    def test_completed_run(self, sample_skill) -> None:
        session = RunSession.create(sample_skill.id, sample_skill.name)
        session.set_status(RunStatus.RUNNING)
        session.completed_steps = [1, 2, 3, 4]
        session.set_status(RunStatus.COMPLETED)

        summary = generate_run_summary(session, sample_skill)
        assert "Completed" in summary
        assert "4/4" in summary

    def test_failed_run(self, sample_skill) -> None:
        session = RunSession.create(sample_skill.id, sample_skill.name)
        session.set_status(RunStatus.RUNNING)
        session.completed_steps = [1]
        session.current_step = 2
        session.set_status(RunStatus.FAILED)

        summary = generate_run_summary(session, sample_skill)
        assert "Failed" in summary
        assert "1/4" in summary

    def test_cancelled_run(self, sample_skill) -> None:
        session = RunSession.create(sample_skill.id, sample_skill.name)
        session.set_status(RunStatus.CANCELLED)

        summary = generate_run_summary(session, sample_skill)
        assert "Cancelled" in summary

    def test_summary_includes_skipped(self, sample_skill) -> None:
        session = RunSession.create(sample_skill.id, sample_skill.name)
        session.set_status(RunStatus.RUNNING)
        session.completed_steps = [1, 2, 3]
        session.skipped_steps = [4]
        session.set_status(RunStatus.COMPLETED)

        summary = generate_run_summary(session, sample_skill)
        assert "skipped" in summary.lower()

    def test_summary_includes_step_details(self, sample_skill) -> None:
        session = RunSession.create(sample_skill.id, sample_skill.name)
        session.set_status(RunStatus.RUNNING)
        session.completed_steps = [1]
        session.set_status(RunStatus.COMPLETED)

        summary = generate_run_summary(session, sample_skill)
        assert "First step" in summary
