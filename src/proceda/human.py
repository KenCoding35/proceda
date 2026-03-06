"""Human interface: protocol and implementations for human-in-the-loop interactions."""

from __future__ import annotations

from typing import Protocol

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from proceda.session import (
    ApprovalDecision,
    ApprovalRequest,
    ClarificationRequest,
    ErrorRecoveryDecision,
    ErrorRecoveryRequest,
)


class HumanInterface(Protocol):
    """Protocol for human-in-the-loop interactions."""

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision: ...

    async def request_clarification(self, request: ClarificationRequest) -> str: ...

    async def request_error_recovery(
        self, request: ErrorRecoveryRequest
    ) -> ErrorRecoveryDecision: ...


class TerminalHumanInterface:
    """Interactive terminal-based human interface using Rich."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        self._console.print()
        label = "PRE-STEP" if request.approval_type == "pre_step" else "POST-STEP"
        self._console.print(
            Panel(
                f"[bold]{label} APPROVAL REQUIRED[/bold]\n\n"
                f"Step {request.step_index}: {request.step_title}\n\n"
                f"{request.context}",
                title="Approval Required",
                border_style="yellow",
            )
        )

        if request.pending_tool_calls:
            table = Table(title="Pending Tool Calls")
            table.add_column("Tool", style="cyan")
            table.add_column("Arguments", style="green")
            for tc in request.pending_tool_calls:
                table.add_row(tc.name, str(tc.arguments))
            self._console.print(table)

        choice = Prompt.ask(
            "[yellow]Decision[/yellow]",
            choices=["approve", "reject", "skip"],
            default="approve",
            console=self._console,
        )
        return ApprovalDecision(choice)

    async def request_clarification(self, request: ClarificationRequest) -> str:
        self._console.print()
        self._console.print(
            Panel(
                f"[bold]CLARIFICATION NEEDED[/bold]\n\n{request.question}",
                title="Clarification",
                border_style="blue",
            )
        )

        if request.options:
            for i, option in enumerate(request.options, 1):
                self._console.print(f"  [{i}] {option}")
            self._console.print()

        return Prompt.ask("[blue]Your answer[/blue]", console=self._console)

    async def request_error_recovery(self, request: ErrorRecoveryRequest) -> ErrorRecoveryDecision:
        self._console.print()
        self._console.print(
            Panel(
                f"[bold]ERROR ENCOUNTERED[/bold]\n\n"
                f"Type: {request.error.error_type}\n"
                f"Message: {request.error.message}",
                title="Error Recovery",
                border_style="red",
            )
        )

        choice = Prompt.ask(
            "[red]Action[/red]",
            choices=["retry", "skip", "cancel"],
            default="cancel",
            console=self._console,
        )
        return ErrorRecoveryDecision(choice)


class AutoApproveHumanInterface:
    """Auto-approves everything. For testing and non-interactive use."""

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        return ApprovalDecision.APPROVE

    async def request_clarification(self, request: ClarificationRequest) -> str:
        if request.options:
            return request.options[0]
        return "Proceed with default."

    async def request_error_recovery(self, request: ErrorRecoveryRequest) -> ErrorRecoveryDecision:
        return ErrorRecoveryDecision.CANCEL


class ScriptedHumanInterface:
    """Returns pre-configured responses. For deterministic testing."""

    def __init__(
        self,
        approval_decisions: list[ApprovalDecision] | None = None,
        clarification_answers: list[str] | None = None,
        error_decisions: list[ErrorRecoveryDecision] | None = None,
    ) -> None:
        self._approvals = list(approval_decisions or [])
        self._clarifications = list(clarification_answers or [])
        self._errors = list(error_decisions or [])

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        if self._approvals:
            return self._approvals.pop(0)
        return ApprovalDecision.APPROVE

    async def request_clarification(self, request: ClarificationRequest) -> str:
        if self._clarifications:
            return self._clarifications.pop(0)
        return "Proceed with default."

    async def request_error_recovery(self, request: ErrorRecoveryRequest) -> ErrorRecoveryDecision:
        if self._errors:
            return self._errors.pop(0)
        return ErrorRecoveryDecision.CANCEL
