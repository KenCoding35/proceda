"""ABOUTME: Tests for the replay CLI command covering valid and invalid run directories.
ABOUTME: Validates error handling for missing runs and successful replay of event logs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from proceda.cli.main import app
from proceda.events import EventType, RunEvent

runner = CliRunner()


def _write_event_log(run_dir: Path, events: list[RunEvent]) -> None:
    """Write a list of RunEvents as JSONL to the run directory."""
    events_file = run_dir / "events.jsonl"
    with open(events_file, "w", encoding="utf-8") as f:
        for event in events:
            f.write(event.to_json() + "\n")


def _write_metadata(run_dir: Path, metadata: dict) -> None:
    meta_path = run_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, default=str), encoding="utf-8")


class TestReplayCommand:
    def test_replay_nonexistent_run_dir(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["replay", "nonexistent-id", "--run-dir", str(tmp_path)])
        assert result.exit_code == 2
        assert "not found" in result.output.lower()

    def test_replay_empty_run_dir(self, tmp_path: Path) -> None:
        """A run directory with no events.jsonl should fail."""
        run_dir = tmp_path / "20260101_120000_abcd1234"
        run_dir.mkdir()
        result = runner.invoke(app, ["replay", str(run_dir)])
        assert result.exit_code == 1
        assert "no event log" in result.output.lower()

    def test_replay_valid_event_log(self, tmp_path: Path) -> None:
        """Replay should succeed with a valid events.jsonl file."""
        run_dir = tmp_path / "20260101_120000_abcd1234"
        run_dir.mkdir()

        created = {"skill_name": "test", "step_count": 1}
        started = {"step_index": 1, "step_title": "Do it"}
        events = [
            RunEvent.create("run-1", EventType.RUN_CREATED, created),
            RunEvent.create("run-1", EventType.STEP_STARTED, started),
            RunEvent.create("run-1", EventType.STEP_COMPLETED, {"step_index": 1}),
            RunEvent.create("run-1", EventType.RUN_COMPLETED, {}),
        ]
        _write_event_log(run_dir, events)

        result = runner.invoke(app, ["replay", str(run_dir)])
        assert result.exit_code == 0

    def test_replay_with_metadata(self, tmp_path: Path) -> None:
        """Replay should render metadata panel when metadata.json exists."""
        run_dir = tmp_path / "20260101_120000_abcd1234"
        run_dir.mkdir()

        _write_metadata(
            run_dir,
            {
                "skill_name": "test-skill",
                "run_id": "run-1",
                "model": "test-model",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        created = {"skill_name": "test-skill", "step_count": 1}
        events = [
            RunEvent.create("run-1", EventType.RUN_CREATED, created),
            RunEvent.create("run-1", EventType.RUN_COMPLETED, {}),
        ]
        _write_event_log(run_dir, events)

        result = runner.invoke(app, ["replay", str(run_dir)])
        assert result.exit_code == 0
        assert "test-skill" in result.output

    def test_replay_finds_run_by_partial_id(self, tmp_path: Path) -> None:
        """Replay should find a run by partial ID match within the run-dir."""
        run_dir = tmp_path / "20260101_120000_abcd1234"
        run_dir.mkdir()
        created = {"skill_name": "test", "step_count": 1}
        events = [
            RunEvent.create("run-1", EventType.RUN_CREATED, created),
            RunEvent.create("run-1", EventType.RUN_COMPLETED, {}),
        ]
        _write_event_log(run_dir, events)

        result = runner.invoke(app, ["replay", "abcd1234", "--run-dir", str(tmp_path)])
        assert result.exit_code == 0

    def test_replay_lists_available_runs_on_not_found(self, tmp_path: Path) -> None:
        """When run is not found, replay should list available runs."""
        existing_run = tmp_path / "20260101_120000_existing1"
        existing_run.mkdir()
        result = runner.invoke(app, ["replay", "nonexistent", "--run-dir", str(tmp_path)])
        assert result.exit_code == 2
        assert "available runs" in result.output.lower()
