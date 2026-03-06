"""Tests for event log writer and reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from skillrunner.events import EventType, RunEvent
from skillrunner.store.event_log import EventLogReader, EventLogWriter, RunDirectoryManager


class TestRunDirectoryManager:
    def test_create_run_dir(self, tmp_path: Path) -> None:
        manager = RunDirectoryManager(str(tmp_path / "runs"))
        run_dir = manager.create_run_dir("test123")
        assert run_dir.exists()
        assert "test123" in run_dir.name

    def test_list_runs_empty(self, tmp_path: Path) -> None:
        manager = RunDirectoryManager(str(tmp_path / "runs"))
        assert manager.list_runs() == []

    def test_list_runs(self, tmp_path: Path) -> None:
        manager = RunDirectoryManager(str(tmp_path / "runs"))
        manager.create_run_dir("run1")
        manager.create_run_dir("run2")
        runs = manager.list_runs()
        assert len(runs) == 2

    def test_find_run_by_path(self, tmp_path: Path) -> None:
        manager = RunDirectoryManager(str(tmp_path / "runs"))
        run_dir = manager.create_run_dir("test123")
        found = manager.find_run(str(run_dir))
        assert found == run_dir

    def test_find_run_by_id(self, tmp_path: Path) -> None:
        manager = RunDirectoryManager(str(tmp_path / "runs"))
        manager.create_run_dir("test123")
        found = manager.find_run("test123")
        assert found is not None
        assert "test123" in found.name

    def test_find_run_not_found(self, tmp_path: Path) -> None:
        manager = RunDirectoryManager(str(tmp_path / "runs"))
        assert manager.find_run("nonexistent") is None


class TestEventLogWriter:
    @pytest.mark.asyncio
    async def test_write_events(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        await writer.open()

        event = RunEvent.create("run_1", EventType.RUN_STARTED)
        await writer.handle(event)
        await writer.close()

        events_file = tmp_path / "events.jsonl"
        assert events_file.exists()
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 1

    @pytest.mark.asyncio
    async def test_write_multiple_events(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        await writer.open()

        for i in range(5):
            event = RunEvent.create("run_1", EventType.STEP_STARTED, {"step_index": i})
            await writer.handle(event)

        await writer.close()

        lines = (tmp_path / "events.jsonl").read_text().strip().split("\n")
        assert len(lines) == 5

    def test_write_metadata(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        writer.write_metadata({"run_id": "test", "skill_name": "my-skill"})
        meta = (tmp_path / "metadata.json").read_text()
        assert "my-skill" in meta

    def test_write_summary(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        writer.write_summary("Run completed successfully.")
        summary = (tmp_path / "summary.txt").read_text()
        assert summary == "Run completed successfully."

    def test_write_artifact(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        path = writer.write_artifact("report.html", "<h1>Done</h1>", "text/html")
        assert path.exists()
        assert path.read_text() == "<h1>Done</h1>"


class TestEventLogReader:
    @pytest.mark.asyncio
    async def test_read_events(self, tmp_path: Path) -> None:
        # Write
        writer = EventLogWriter(tmp_path)
        await writer.open()
        events_written = []
        for i in range(3):
            event = RunEvent.create("run_1", EventType.STEP_STARTED, {"step_index": i + 1})
            await writer.handle(event)
            events_written.append(event)
        await writer.close()

        # Read
        reader = EventLogReader(tmp_path)
        events_read = reader.read_events()
        assert len(events_read) == 3
        assert events_read[0].payload["step_index"] == 1
        assert events_read[2].payload["step_index"] == 3

    def test_read_metadata(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        writer.write_metadata({"run_id": "test"})

        reader = EventLogReader(tmp_path)
        meta = reader.read_metadata()
        assert meta["run_id"] == "test"

    def test_read_summary(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        writer.write_summary("All done")

        reader = EventLogReader(tmp_path)
        assert reader.read_summary() == "All done"

    def test_read_no_summary(self, tmp_path: Path) -> None:
        reader = EventLogReader(tmp_path)
        assert reader.read_summary() is None

    def test_exists_property(self, tmp_path: Path) -> None:
        reader = EventLogReader(tmp_path)
        assert not reader.exists

    @pytest.mark.asyncio
    async def test_iter_events(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        await writer.open()
        for i in range(3):
            await writer.handle(RunEvent.create("r", EventType.STEP_STARTED, {"i": i}))
        await writer.close()

        reader = EventLogReader(tmp_path)
        events = list(reader.iter_events())
        assert len(events) == 3
