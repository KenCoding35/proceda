# ABOUTME: Tests for executor bug fixes: iteration exhaustion, pre-approval context,
# ABOUTME: and status.changed event on failure.

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from proceda.events import CollectorEventSink, EventType
from proceda.human import AutoApproveHumanInterface
from proceda.internal.executor import Executor
from proceda.llm.runtime import LLMResponse
from proceda.session import ApprovalDecision, RunSession, RunStatus, ToolCall
from proceda.skills.parser import parse_skill

ONE_STEP_SKILL = """\
---
name: one-step
description: A single step skill
---

### Step 1: Do something
Do the thing.
"""

PRE_APPROVAL_SKILL = """\
---
name: pre-approval-test
description: Skill with pre-approval step
---

### Step 1: Dangerous step
[PRE-APPROVAL REQUIRED]
Run the dangerous operation on production.
"""


def _make_complete_response(summary: str = "Done.") -> LLMResponse:
    return LLMResponse(
        content=summary,
        tool_calls=[
            ToolCall(
                id=ToolCall.generate_id(),
                name="complete_step",
                arguments={"summary": summary},
            )
        ],
    )


def _make_text_only_response(text: str = "Thinking...") -> LLMResponse:
    return LLMResponse(content=text, tool_calls=[])


class TestIterationExhaustion:
    """Bug 1: Step should fail (not silently complete) when iterations are exhausted."""

    @pytest.mark.asyncio
    async def test_step_fails_on_iteration_exhaustion(self) -> None:
        skill = parse_skill(ONE_STEP_SKILL)
        session = RunSession.create(skill.id, skill.name)
        collector = CollectorEventSink()

        # LLM always returns text-only responses, never calls complete_step
        call_count = 0

        async def mock_complete(messages, tools=None):
            nonlocal call_count
            call_count += 1
            return _make_text_only_response(f"Still thinking... ({call_count})")

        llm = AsyncMock()
        llm.complete = mock_complete
        llm.format_messages = lambda msgs: [{"role": "user", "content": "test"}]

        executor = Executor(
            skill=skill,
            session=session,
            llm=llm,
            tool_executor=None,
            human=AutoApproveHumanInterface(),
            emit=collector.handle,
        )

        await executor.execute()

        assert session.status == RunStatus.FAILED
        assert session.pending_error is not None
        assert "exhausted" in session.pending_error.message.lower()
        # Step should NOT be in completed_steps
        assert 1 not in session.completed_steps


class TestPreApprovalContext:
    """Bug 3: Pre-approval should include step title and content in context."""

    @pytest.mark.asyncio
    async def test_pre_approval_context_contains_step_content(self) -> None:
        skill = parse_skill(PRE_APPROVAL_SKILL)
        session = RunSession.create(skill.id, skill.name)
        collector = CollectorEventSink()

        captured_requests: list = []

        class CapturingHuman:
            async def request_approval(self, request):
                captured_requests.append(request)
                return ApprovalDecision.APPROVE

            async def request_clarification(self, request):
                return "ok"

            async def request_error_recovery(self, request):
                from proceda.session import ErrorRecoveryDecision

                return ErrorRecoveryDecision.CANCEL

        async def mock_complete(messages, tools=None):
            return _make_complete_response("Done.")

        llm = AsyncMock()
        llm.complete = mock_complete
        llm.format_messages = lambda msgs: [{"role": "user", "content": "test"}]

        executor = Executor(
            skill=skill,
            session=session,
            llm=llm,
            tool_executor=None,
            human=CapturingHuman(),
            emit=collector.handle,
        )

        await executor.execute()

        assert len(captured_requests) == 1
        context = captured_requests[0].context
        assert "Dangerous step" in context
        assert "dangerous operation on production" in context


class TestFailureStatusChanged:
    """Bug 6: Failure path should emit STATUS_CHANGED event."""

    @pytest.mark.asyncio
    async def test_failure_emits_status_changed(self) -> None:
        skill = parse_skill(ONE_STEP_SKILL)
        session = RunSession.create(skill.id, skill.name)
        collector = CollectorEventSink()

        async def mock_complete(messages, tools=None):
            raise RuntimeError("LLM exploded")

        llm = AsyncMock()
        llm.complete = mock_complete
        llm.format_messages = lambda msgs: [{"role": "user", "content": "test"}]

        executor = Executor(
            skill=skill,
            session=session,
            llm=llm,
            tool_executor=None,
            human=AutoApproveHumanInterface(),
            emit=collector.handle,
        )

        await executor.execute()

        assert session.status == RunStatus.FAILED

        event_types = [e.type for e in collector.events]
        assert EventType.RUN_FAILED in event_types
        assert EventType.STATUS_CHANGED in event_types

        # STATUS_CHANGED with "failed" should come after RUN_FAILED
        status_events = [
            e
            for e in collector.events
            if e.type == EventType.STATUS_CHANGED and e.payload.get("status") == "failed"
        ]
        assert len(status_events) == 1
