"""ABOUTME: Tests for event log writer, reader, run directory manager, and secret redaction.
ABOUTME: Covers lifecycle edge cases, reader robustness, and redaction of nested structures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proceda.events import EventType, RunEvent
from proceda.store.event_log import (
    EventLogReader,
    EventLogWriter,
    RunDirectoryManager,
    _redact_dict,
)


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


class TestRedactSecrets:
    """Bug 2: redact_secrets config should actually redact secret-like fields."""

    def test_redact_dict_scrubs_secret_keys(self) -> None:
        data = {"api_key": "sk-123", "name": "test", "auth_token": "tok-abc"}
        result = _redact_dict(data)
        assert result["api_key"] == "**REDACTED**"
        assert result["auth_token"] == "**REDACTED**"
        assert result["name"] == "test"

    def test_redact_dict_handles_nested(self) -> None:
        data = {"config": {"password": "hunter2", "host": "localhost"}}
        result = _redact_dict(data)
        assert result["config"]["password"] == "**REDACTED**"
        assert result["config"]["host"] == "localhost"

    def test_redact_dict_handles_lists(self) -> None:
        data = {"items": [{"secret": "s1"}, {"value": "v1"}]}
        result = _redact_dict(data)
        assert result["items"][0]["secret"] == "**REDACTED**"
        assert result["items"][1]["value"] == "v1"

    def test_metadata_redacted_when_enabled(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path, redact_secrets=True)
        writer.write_metadata({"run_id": "test", "api_key": "sk-secret-123"})
        meta = json.loads((tmp_path / "metadata.json").read_text())
        assert meta["api_key"] == "**REDACTED**"
        assert meta["run_id"] == "test"

    def test_metadata_not_redacted_when_disabled(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path, redact_secrets=False)
        writer.write_metadata({"run_id": "test", "api_key": "sk-secret-123"})
        meta = json.loads((tmp_path / "metadata.json").read_text())
        assert meta["api_key"] == "sk-secret-123"

    @pytest.mark.asyncio
    async def test_events_redacted_when_enabled(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path, redact_secrets=True)
        await writer.open()
        event = RunEvent.create("r1", EventType.TOOL_CALLED, {"api_key": "sk-123", "tool": "x"})
        await writer.handle(event)
        await writer.close()

        reader = EventLogReader(tmp_path)
        events = reader.read_events()
        assert events[0].payload["api_key"] == "**REDACTED**"
        assert events[0].payload["tool"] == "x"


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


class TestEventLogWriterLifecycle:
    @pytest.mark.asyncio
    async def test_auto_open_on_first_handle(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        # Don't call open(), just handle() — should auto-open
        event = RunEvent.create("run_1", EventType.RUN_STARTED)
        await writer.handle(event)
        await writer.close()

        events_file = tmp_path / "events.jsonl"
        assert events_file.exists()
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 1

    @pytest.mark.asyncio
    async def test_close_idempotent(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        await writer.open()
        await writer.handle(RunEvent.create("r", EventType.RUN_STARTED))
        await writer.close()
        await writer.close()  # second close should not error

    @pytest.mark.asyncio
    async def test_close_without_open(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        await writer.close()  # never opened — should not error

    @pytest.mark.asyncio
    async def test_write_after_close_reopens(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        await writer.open()
        await writer.handle(RunEvent.create("r", EventType.RUN_STARTED))
        await writer.close()

        # Writing after close should auto-reopen
        await writer.handle(RunEvent.create("r", EventType.RUN_COMPLETED))
        await writer.close()

        reader = EventLogReader(tmp_path)
        events = reader.read_events()
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_events_appended_across_reopen(self, tmp_path: Path) -> None:
        writer = EventLogWriter(tmp_path)
        await writer.open()
        await writer.handle(RunEvent.create("r", EventType.STEP_STARTED, {"i": 1}))
        await writer.handle(RunEvent.create("r", EventType.STEP_STARTED, {"i": 2}))
        await writer.close()

        # Reopen and write two more
        await writer.handle(RunEvent.create("r", EventType.STEP_STARTED, {"i": 3}))
        await writer.handle(RunEvent.create("r", EventType.STEP_STARTED, {"i": 4}))
        await writer.close()

        reader = EventLogReader(tmp_path)
        events = reader.read_events()
        assert len(events) == 4
        assert [e.payload["i"] for e in events] == [1, 2, 3, 4]


class TestEventLogReaderEdgeCases:
    def test_read_empty_events_file(self, tmp_path: Path) -> None:
        (tmp_path / "events.jsonl").write_text("", encoding="utf-8")
        reader = EventLogReader(tmp_path)
        assert reader.read_events() == []

    def test_read_events_with_blank_lines(self, tmp_path: Path) -> None:
        # Write events with blank lines interspersed
        writer_events = [
            RunEvent.create("r", EventType.STEP_STARTED, {"i": 1}),
            RunEvent.create("r", EventType.STEP_STARTED, {"i": 2}),
        ]
        content = writer_events[0].to_json() + "\n\n" + writer_events[1].to_json() + "\n\n"
        (tmp_path / "events.jsonl").write_text(content, encoding="utf-8")

        reader = EventLogReader(tmp_path)
        events = reader.read_events()
        assert len(events) == 2

    def test_iter_events_empty(self, tmp_path: Path) -> None:
        (tmp_path / "events.jsonl").write_text("", encoding="utf-8")
        reader = EventLogReader(tmp_path)
        assert list(reader.iter_events()) == []

    def test_read_metadata_missing_file(self, tmp_path: Path) -> None:
        reader = EventLogReader(tmp_path)
        assert reader.read_metadata() == {}


class TestRunDirectoryManagerEdgeCases:
    def test_create_with_auto_id(self, tmp_path: Path) -> None:
        manager = RunDirectoryManager(str(tmp_path / "runs"))
        run_dir = manager.create_run_dir()  # no run_id — auto-generate
        assert run_dir.exists()
        # Directory name should have timestamp + 8-char hex ID
        assert len(run_dir.name.split("_")) >= 3

    def test_list_runs_sorted_newest_first(self, tmp_path: Path) -> None:
        import time

        manager = RunDirectoryManager(str(tmp_path / "runs"))
        dir1 = manager.create_run_dir("aaa")
        time.sleep(1.1)  # ensure different timestamp
        dir2 = manager.create_run_dir("bbb")

        runs = manager.list_runs()
        assert len(runs) == 2
        # Newest (dir2) should be first since names sort by timestamp
        assert runs[0] == dir2
        assert runs[1] == dir1

    def test_find_run_partial_match(self, tmp_path: Path) -> None:
        manager = RunDirectoryManager(str(tmp_path / "runs"))
        manager.create_run_dir("abcdef12")

        # Search by partial ID prefix
        found = manager.find_run("abcdef")
        assert found is not None
        assert "abcdef12" in found.name


class TestRedactDictEdgeCases:
    def test_empty_dict(self) -> None:
        assert _redact_dict({}) == {}

    def test_deeply_nested(self) -> None:
        data = {
            "level1": {
                "level2": {
                    "level3": {"api_key": "deep-secret", "name": "keep"},
                    "password": "mid-secret",
                },
                "token": "top-secret",
            }
        }
        result = _redact_dict(data)
        assert result["level1"]["token"] == "**REDACTED**"
        assert result["level1"]["level2"]["password"] == "**REDACTED**"
        assert result["level1"]["level2"]["level3"]["api_key"] == "**REDACTED**"
        assert result["level1"]["level2"]["level3"]["name"] == "keep"

    def test_list_with_mixed_types(self) -> None:
        data = {
            "items": [
                {"secret": "s1"},
                "plain-string",
                42,
                {"value": "safe"},
            ]
        }
        result = _redact_dict(data)
        assert result["items"][0]["secret"] == "**REDACTED**"
        assert result["items"][1] == "plain-string"
        assert result["items"][2] == 42
        assert result["items"][3]["value"] == "safe"

    def test_case_insensitive_match(self) -> None:
        data = {
            "API_KEY": "k1",
            "api_key": "k2",
            "Api_Key": "k3",
            "name": "keep",
        }
        result = _redact_dict(data)
        assert result["API_KEY"] == "**REDACTED**"
        assert result["api_key"] == "**REDACTED**"
        assert result["Api_Key"] == "**REDACTED**"
        assert result["name"] == "keep"

    def test_token_count_fields_not_redacted(self) -> None:
        data = {
            "prompt_tokens": 1234,
            "completion_tokens": 567,
            "total_tokens": 1801,
            "cumulative_total_tokens": 5000,
            "token": "secret-value",
            "auth_token": "also-secret",
        }
        result = _redact_dict(data)
        assert result["prompt_tokens"] == 1234
        assert result["completion_tokens"] == 567
        assert result["total_tokens"] == 1801
        assert result["cumulative_total_tokens"] == 5000
        assert result["token"] == "**REDACTED**"
        assert result["auth_token"] == "**REDACTED**"
