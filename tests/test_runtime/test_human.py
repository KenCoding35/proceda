"""Tests for human interface implementations."""

from __future__ import annotations

import pytest

from proceda.human import AutoApproveHumanInterface, ScriptedHumanInterface
from proceda.session import (
    ApprovalDecision,
    ApprovalRequest,
    ClarificationRequest,
    ErrorContext,
    ErrorRecoveryDecision,
    ErrorRecoveryRequest,
)


class TestAutoApproveHumanInterface:
    @pytest.mark.asyncio
    async def test_approves_everything(self) -> None:
        human = AutoApproveHumanInterface()
        request = ApprovalRequest(
            step_index=1,
            step_title="Test",
            approval_type="pre_step",
            context="Context",
        )
        result = await human.request_approval(request)
        assert result == ApprovalDecision.APPROVE

    @pytest.mark.asyncio
    async def test_clarification_with_options(self) -> None:
        human = AutoApproveHumanInterface()
        request = ClarificationRequest(question="Which?", options=["A", "B"])
        result = await human.request_clarification(request)
        assert result == "A"

    @pytest.mark.asyncio
    async def test_clarification_without_options(self) -> None:
        human = AutoApproveHumanInterface()
        request = ClarificationRequest(question="What?")
        result = await human.request_clarification(request)
        assert result == "Proceed with default."

    @pytest.mark.asyncio
    async def test_error_recovery_cancels(self) -> None:
        human = AutoApproveHumanInterface()
        request = ErrorRecoveryRequest(error=ErrorContext(error_type="TestError", message="oops"))
        result = await human.request_error_recovery(request)
        assert result == ErrorRecoveryDecision.CANCEL


class TestScriptedHumanInterface:
    @pytest.mark.asyncio
    async def test_scripted_approvals(self) -> None:
        human = ScriptedHumanInterface(
            approval_decisions=[ApprovalDecision.REJECT, ApprovalDecision.APPROVE]
        )
        req = ApprovalRequest(step_index=1, step_title="T", approval_type="pre_step", context="C")

        r1 = await human.request_approval(req)
        assert r1 == ApprovalDecision.REJECT

        r2 = await human.request_approval(req)
        assert r2 == ApprovalDecision.APPROVE

    @pytest.mark.asyncio
    async def test_scripted_clarifications(self) -> None:
        human = ScriptedHumanInterface(clarification_answers=["Use option B"])
        req = ClarificationRequest(question="Which?")
        result = await human.request_clarification(req)
        assert result == "Use option B"

    @pytest.mark.asyncio
    async def test_defaults_when_empty(self) -> None:
        human = ScriptedHumanInterface()
        req = ApprovalRequest(step_index=1, step_title="T", approval_type="pre_step", context="C")
        result = await human.request_approval(req)
        assert result == ApprovalDecision.APPROVE

    @pytest.mark.asyncio
    async def test_scripted_error_recovery(self) -> None:
        human = ScriptedHumanInterface(error_decisions=[ErrorRecoveryDecision.RETRY])
        req = ErrorRecoveryRequest(error=ErrorContext(error_type="E", message="m"))
        result = await human.request_error_recovery(req)
        assert result == ErrorRecoveryDecision.RETRY
