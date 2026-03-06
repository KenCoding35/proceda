"""Tests for session data models."""

from __future__ import annotations

from skillrunner.session import (
    ApprovalRequest,
    ClarificationRequest,
    RunMessage,
    RunResult,
    RunSession,
    RunStatus,
    ToolCall,
)


class TestRunStatus:
    def test_terminal_states(self) -> None:
        assert RunStatus.COMPLETED.is_terminal
        assert RunStatus.FAILED.is_terminal
        assert RunStatus.CANCELLED.is_terminal

    def test_non_terminal_states(self) -> None:
        assert not RunStatus.CREATED.is_terminal
        assert not RunStatus.RUNNING.is_terminal
        assert not RunStatus.AWAITING_APPROVAL.is_terminal

    def test_active_states(self) -> None:
        assert RunStatus.RUNNING.is_active
        assert RunStatus.AWAITING_APPROVAL.is_active
        assert RunStatus.AWAITING_INPUT.is_active

    def test_inactive_states(self) -> None:
        assert not RunStatus.CREATED.is_active
        assert not RunStatus.COMPLETED.is_active
        assert not RunStatus.FAILED.is_active


class TestToolCall:
    def test_create(self) -> None:
        tc = ToolCall(id="tc_123", name="test_tool", arguments={"key": "value"})
        assert tc.id == "tc_123"
        assert tc.name == "test_tool"
        assert tc.arguments == {"key": "value"}

    def test_generate_id(self) -> None:
        id1 = ToolCall.generate_id()
        id2 = ToolCall.generate_id()
        assert id1.startswith("tc_")
        assert id2.startswith("tc_")
        assert id1 != id2


class TestRunMessage:
    def test_create(self) -> None:
        msg = RunMessage.create("user", "hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert msg.id.startswith("msg_")
        assert msg.timestamp is not None

    def test_create_with_tool_call_id(self) -> None:
        msg = RunMessage.create("tool", "result", tool_call_id="tc_123")
        assert msg.tool_call_id == "tc_123"

    def test_create_with_tool_calls(self) -> None:
        tc = ToolCall(id="tc_1", name="tool", arguments={})
        msg = RunMessage.create("assistant", "text", tool_calls=[tc])
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1


class TestRunSession:
    def test_create(self) -> None:
        session = RunSession.create("skill_1", "Test Skill")
        assert session.id.startswith("run_")
        assert session.skill_id == "skill_1"
        assert session.skill_name == "Test Skill"
        assert session.status == RunStatus.CREATED
        assert session.current_step == 1

    def test_create_with_variables(self) -> None:
        session = RunSession.create("s", "S", variables={"key": "val"})
        assert session.variables == {"key": "val"}

    def test_set_status_running(self) -> None:
        session = RunSession.create("s", "S")
        session.set_status(RunStatus.RUNNING)
        assert session.status == RunStatus.RUNNING
        assert session.started_at is not None

    def test_set_status_completed(self) -> None:
        session = RunSession.create("s", "S")
        session.set_status(RunStatus.RUNNING)
        session.set_status(RunStatus.COMPLETED)
        assert session.status == RunStatus.COMPLETED
        assert session.completed_at is not None

    def test_touch_updates_timestamp(self) -> None:
        session = RunSession.create("s", "S")
        old_time = session.last_activity_at
        session.touch()
        assert session.last_activity_at >= old_time

    def test_add_message(self) -> None:
        session = RunSession.create("s", "S")
        msg = RunMessage.create("user", "hello")
        session.add_message(msg)
        assert len(session.messages) == 1
        assert session.messages[0].content == "hello"

    def test_complete_current_step(self) -> None:
        session = RunSession.create("s", "S")
        session.complete_current_step()
        assert 1 in session.completed_steps

    def test_advance_step(self) -> None:
        session = RunSession.create("s", "S")
        assert session.current_step == 1
        session.advance_step()
        assert session.current_step == 2
        assert len(session.step_tool_results) == 0
        assert len(session.pending_tool_calls) == 0


class TestRunResult:
    def test_create(self) -> None:
        result = RunResult(
            session_id="run_123",
            status=RunStatus.COMPLETED,
            summary="All done",
            completed_steps=3,
            total_steps=3,
        )
        assert result.session_id == "run_123"
        assert result.status == RunStatus.COMPLETED
        assert result.failed_step is None

    def test_failed_result(self) -> None:
        result = RunResult(
            session_id="run_123",
            status=RunStatus.FAILED,
            summary="Failed at step 2",
            completed_steps=1,
            total_steps=3,
            failed_step=2,
        )
        assert result.failed_step == 2


class TestApprovalRequest:
    def test_create(self) -> None:
        req = ApprovalRequest(
            step_index=1,
            step_title="Test Step",
            approval_type="pre_step",
            context="Need approval",
        )
        assert req.step_index == 1
        assert req.approval_type == "pre_step"


class TestClarificationRequest:
    def test_create_with_options(self) -> None:
        req = ClarificationRequest(
            question="Which option?",
            options=["A", "B", "C"],
        )
        assert len(req.options) == 3

    def test_create_without_options(self) -> None:
        req = ClarificationRequest(question="What?")
        assert req.options == []
