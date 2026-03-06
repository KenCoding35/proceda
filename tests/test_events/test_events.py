"""Tests for the event model and sinks."""

from __future__ import annotations

import json

import pytest

from proceda.events import (
    CollectorEventSink,
    CompositeEventSink,
    EventType,
    NullEventSink,
    RunEvent,
)


class TestRunEvent:
    def test_create(self) -> None:
        event = RunEvent.create("run_123", EventType.RUN_CREATED, {"skill_name": "test"})
        assert event.id.startswith("evt_")
        assert event.run_id == "run_123"
        assert event.type == EventType.RUN_CREATED
        assert event.payload["skill_name"] == "test"

    def test_create_without_payload(self) -> None:
        event = RunEvent.create("run_123", EventType.RUN_STARTED)
        assert event.payload == {}

    def test_to_dict(self) -> None:
        event = RunEvent.create("run_123", EventType.TOOL_CALLED, {"tool_name": "test"})
        d = event.to_dict()
        assert d["run_id"] == "run_123"
        assert d["type"] == "tool.called"
        assert d["payload"]["tool_name"] == "test"
        assert "id" in d
        assert "timestamp" in d

    def test_to_json(self) -> None:
        event = RunEvent.create("run_123", EventType.STEP_STARTED, {"step_index": 1})
        json_str = event.to_json()
        parsed = json.loads(json_str)
        assert parsed["type"] == "step.started"

    def test_from_dict(self) -> None:
        event = RunEvent.create("run_123", EventType.MESSAGE_ASSISTANT, {"content": "hello"})
        d = event.to_dict()
        restored = RunEvent.from_dict(d)
        assert restored.id == event.id
        assert restored.type == event.type
        assert restored.payload == event.payload

    def test_from_json(self) -> None:
        event = RunEvent.create("run_123", EventType.TOOL_COMPLETED, {"result": "ok"})
        json_str = event.to_json()
        restored = RunEvent.from_json(json_str)
        assert restored.id == event.id
        assert restored.type == EventType.TOOL_COMPLETED

    def test_json_roundtrip(self) -> None:
        event = RunEvent.create(
            "run_123",
            EventType.APPROVAL_REQUESTED,
            {"step_index": 2, "approval_type": "pre_step"},
        )
        restored = RunEvent.from_json(event.to_json())
        assert restored.to_dict() == event.to_dict()


class TestEventType:
    def test_all_event_types_have_values(self) -> None:
        for et in EventType:
            assert isinstance(et.value, str)
            assert "." in et.value

    def test_event_type_from_value(self) -> None:
        assert EventType("run.created") == EventType.RUN_CREATED
        assert EventType("tool.called") == EventType.TOOL_CALLED


class TestNullEventSink:
    @pytest.mark.asyncio
    async def test_handle_does_nothing(self) -> None:
        sink = NullEventSink()
        event = RunEvent.create("run_123", EventType.RUN_STARTED)
        await sink.handle(event)  # Should not raise


class TestCollectorEventSink:
    @pytest.mark.asyncio
    async def test_collects_events(self) -> None:
        sink = CollectorEventSink()
        e1 = RunEvent.create("run_123", EventType.RUN_STARTED)
        e2 = RunEvent.create("run_123", EventType.STEP_STARTED, {"step_index": 1})
        await sink.handle(e1)
        await sink.handle(e2)
        assert len(sink.events) == 2

    @pytest.mark.asyncio
    async def test_of_type_filter(self) -> None:
        sink = CollectorEventSink()
        await sink.handle(RunEvent.create("r", EventType.RUN_STARTED))
        await sink.handle(RunEvent.create("r", EventType.STEP_STARTED))
        await sink.handle(RunEvent.create("r", EventType.STEP_COMPLETED))
        await sink.handle(RunEvent.create("r", EventType.STEP_STARTED))

        step_starts = sink.of_type(EventType.STEP_STARTED)
        assert len(step_starts) == 2


class TestCompositeEventSink:
    @pytest.mark.asyncio
    async def test_fans_out_to_multiple_sinks(self) -> None:
        s1 = CollectorEventSink()
        s2 = CollectorEventSink()
        composite = CompositeEventSink([s1, s2])

        event = RunEvent.create("run_123", EventType.RUN_CREATED)
        await composite.handle(event)

        assert len(s1.events) == 1
        assert len(s2.events) == 1
        assert s1.events[0].id == s2.events[0].id

    @pytest.mark.asyncio
    async def test_add_sink(self) -> None:
        composite = CompositeEventSink()
        s1 = CollectorEventSink()
        composite.add(s1)

        await composite.handle(RunEvent.create("r", EventType.RUN_STARTED))
        assert len(s1.events) == 1

    @pytest.mark.asyncio
    async def test_preserves_order(self) -> None:
        calls: list[int] = []

        class OrderedSink:
            def __init__(self, idx: int):
                self.idx = idx

            async def handle(self, event: RunEvent) -> None:
                calls.append(self.idx)

        composite = CompositeEventSink([OrderedSink(1), OrderedSink(2), OrderedSink(3)])
        await composite.handle(RunEvent.create("r", EventType.RUN_STARTED))
        assert calls == [1, 2, 3]
