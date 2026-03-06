"""Tests for replay functionality."""

from __future__ import annotations

from pathlib import Path

import pytest

from skillrunner.events import EventType, RunEvent
from skillrunner.replay import ReplayRenderer
from skillrunner.store.event_log import EventLogWriter


class TestReplayRenderer:
    @pytest.mark.asyncio
    async def _write_sample_events(self, run_dir: Path) -> None:
        writer = EventLogWriter(run_dir)
        writer.write_metadata(
            {
                "run_id": "run_test",
                "skill_name": "test-skill",
                "model": "test-model",
            }
        )
        await writer.open()

        rid = "run_test"
        events = [
            RunEvent.create(
                rid,
                EventType.RUN_CREATED,
                {
                    "skill_name": "test-skill",
                    "step_count": 2,
                },
            ),
            RunEvent.create(rid, EventType.STATUS_CHANGED, {"status": "running"}),
            RunEvent.create(
                rid,
                EventType.STEP_STARTED,
                {
                    "step_index": 1,
                    "step_title": "First",
                },
            ),
            RunEvent.create(
                rid,
                EventType.MESSAGE_ASSISTANT,
                {
                    "content": "Working on step 1",
                },
            ),
            RunEvent.create(
                rid,
                EventType.TOOL_CALLED,
                {
                    "tool_name": "test__tool",
                    "arguments": {"x": 1},
                },
            ),
            RunEvent.create(
                rid,
                EventType.TOOL_COMPLETED,
                {
                    "tool_name": "test__tool",
                    "result": "done",
                },
            ),
            RunEvent.create(
                rid,
                EventType.STEP_COMPLETED,
                {
                    "step_index": 1,
                    "step_title": "First",
                },
            ),
            RunEvent.create(
                rid,
                EventType.STEP_STARTED,
                {
                    "step_index": 2,
                    "step_title": "Second",
                },
            ),
            RunEvent.create(
                rid,
                EventType.STEP_COMPLETED,
                {
                    "step_index": 2,
                    "step_title": "Second",
                },
            ),
            RunEvent.create(rid, EventType.RUN_COMPLETED, {}),
        ]

        for event in events:
            await writer.handle(event)
        await writer.close()

        writer.write_summary("Run completed. 2/2 steps done.")

    @pytest.mark.asyncio
    async def test_replay_success(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "test_run"
        run_dir.mkdir()
        await self._write_sample_events(run_dir)

        renderer = ReplayRenderer(speed=0)
        success = renderer.replay(run_dir)
        assert success

    def test_replay_missing_log(self, tmp_path: Path) -> None:
        renderer = ReplayRenderer()
        success = renderer.replay(tmp_path)
        assert not success

    @pytest.mark.asyncio
    async def test_replay_without_network(self, tmp_path: Path) -> None:
        """Replay should work without any network access."""
        run_dir = tmp_path / "offline_run"
        run_dir.mkdir()
        await self._write_sample_events(run_dir)

        renderer = ReplayRenderer(speed=0)
        success = renderer.replay(run_dir)
        assert success
