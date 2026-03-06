"""Main Textual application for SkillRunner TUI."""

from __future__ import annotations

import asyncio
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header

from skillrunner.config import SkillRunnerConfig
from skillrunner.events import EventType, RunEvent
from skillrunner.human import HumanInterface
from skillrunner.runtime import Runtime
from skillrunner.session import (
    ApprovalDecision,
    ApprovalRequest,
    ClarificationRequest,
    ErrorRecoveryDecision,
    ErrorRecoveryRequest,
)
from skillrunner.skill import Skill
from skillrunner.tui.widgets import (
    MessageStreamWidget,
    SkillHeaderWidget,
    StatusBarWidget,
    StepListWidget,
    ToolActivityWidget,
)


class TUIHumanInterface:
    """Human interface that integrates with the Textual TUI."""

    def __init__(self, app: SkillRunnerApp) -> None:
        self._app = app

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        self._app.show_approval(request)
        result = await self._app.wait_for_approval()
        return result

    async def request_clarification(self, request: ClarificationRequest) -> str:
        self._app.show_clarification(request)
        result = await self._app.wait_for_clarification()
        return result

    async def request_error_recovery(self, request: ErrorRecoveryRequest) -> ErrorRecoveryDecision:
        return ErrorRecoveryDecision.CANCEL


class TUIEventSink:
    """Feeds events to the TUI."""

    def __init__(self, app: SkillRunnerApp) -> None:
        self._app = app

    async def handle(self, event: RunEvent) -> None:
        self._app.call_from_thread(self._app.on_run_event, event)


class SkillRunnerApp(App[None]):
    """Full-screen TUI for running skills in dev mode."""

    TITLE = "SkillRunner Dev"

    CSS = """
    #main-container {
        layout: horizontal;
    }
    #sidebar {
        width: 35;
        border-right: solid $primary;
    }
    #content {
        width: 1fr;
    }
    #messages {
        height: 1fr;
        border-bottom: solid $primary;
    }
    #tools {
        height: 12;
    }
    StepListWidget {
        height: 1fr;
    }
    SkillHeaderWidget {
        height: auto;
        max-height: 6;
    }
    StatusBarWidget {
        height: 3;
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "approve", "Approve", show=False),
        Binding("r", "reject", "Reject", show=False),
        Binding("s", "skip", "Skip", show=False),
        Binding("c", "confirm_clarification", "Confirm", show=False),
        Binding("?", "help", "Help", show=True),
    ]

    def __init__(
        self,
        skill: Skill,
        config: SkillRunnerConfig,
        variables: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self._skill = skill
        self._config = config
        self._variables = variables or {}
        self._approval_future: asyncio.Future[ApprovalDecision] | None = None
        self._clarification_future: asyncio.Future[str] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            with Vertical(id="sidebar"):
                yield SkillHeaderWidget(self._skill)
                yield StepListWidget(self._skill)
            with Vertical(id="content"):
                yield MessageStreamWidget(id="messages")
                yield ToolActivityWidget(id="tools")
        yield StatusBarWidget()
        yield Footer()

    async def on_mount(self) -> None:
        """Start the skill execution when the app mounts."""
        self.run_worker(self._execute_skill, thread=True)

    async def _execute_skill(self) -> None:
        """Run the skill in a background thread."""
        human = TUIHumanInterface(self)
        runtime = Runtime(config=self._config, human=human)
        sink = TUIEventSink(self)

        await runtime.run(
            self._skill,
            variables=self._variables,
            event_sinks=[sink],
        )

    def on_run_event(self, event: RunEvent) -> None:
        """Handle a runtime event in the TUI."""
        t = event.type
        p = event.payload

        # Update step list
        step_list = self.query_one(StepListWidget)

        if t == EventType.STEP_STARTED:
            step_list.set_active_step(p.get("step_index", 0))
        elif t == EventType.STEP_COMPLETED:
            step_list.mark_completed(p.get("step_index", 0))
        elif t == EventType.STEP_SKIPPED:
            step_list.mark_skipped(p.get("step_index", 0))

        # Update messages
        messages = self.query_one(MessageStreamWidget)

        if t == EventType.MESSAGE_ASSISTANT:
            messages.add_message("assistant", p.get("content", ""))
        elif t == EventType.MESSAGE_REASONING:
            messages.add_message("reasoning", p.get("content", ""))
        elif t == EventType.CLARIFICATION_REQUESTED:
            messages.add_message("system", f"Clarification: {p.get('question', '')}")
        elif t == EventType.APPROVAL_REQUESTED:
            messages.add_message(
                "system",
                f"Approval required: {p.get('approval_type', '')} for step {p.get('step_index', '')}",
            )

        # Update tool activity
        tools = self.query_one(ToolActivityWidget)

        if t == EventType.TOOL_CALLED:
            tools.add_call(p.get("tool_name", ""), p.get("arguments", {}))
        elif t == EventType.TOOL_COMPLETED:
            tools.add_result(p.get("tool_name", ""), p.get("result", ""), success=True)
        elif t == EventType.TOOL_FAILED:
            tools.add_result(p.get("tool_name", ""), p.get("error", ""), success=False)

        # Update status
        status = self.query_one(StatusBarWidget)

        if t == EventType.STATUS_CHANGED:
            status.update_status(p.get("status", ""))
        elif t == EventType.RUN_COMPLETED:
            status.update_status("completed")
        elif t == EventType.RUN_FAILED:
            status.update_status("failed")
        elif t == EventType.SUMMARY_GENERATED:
            messages.add_message("summary", p.get("summary", ""))

    def show_approval(self, request: ApprovalRequest) -> None:
        """Show approval prompt in TUI."""
        status = self.query_one(StatusBarWidget)
        status.update_status("awaiting_approval")
        status.show_approval_hint()
        loop = asyncio.get_event_loop()
        self._approval_future = loop.create_future()

    async def wait_for_approval(self) -> ApprovalDecision:
        if self._approval_future:
            return await self._approval_future
        return ApprovalDecision.APPROVE

    def show_clarification(self, request: ClarificationRequest) -> None:
        """Show clarification prompt in TUI."""
        status = self.query_one(StatusBarWidget)
        status.update_status("awaiting_input")
        loop = asyncio.get_event_loop()
        self._clarification_future = loop.create_future()

    async def wait_for_clarification(self) -> str:
        if self._clarification_future:
            return await self._clarification_future
        return "Proceed with default."

    def action_approve(self) -> None:
        if self._approval_future and not self._approval_future.done():
            self._approval_future.set_result(ApprovalDecision.APPROVE)

    def action_reject(self) -> None:
        if self._approval_future and not self._approval_future.done():
            self._approval_future.set_result(ApprovalDecision.REJECT)

    def action_skip(self) -> None:
        if self._approval_future and not self._approval_future.done():
            self._approval_future.set_result(ApprovalDecision.SKIP)

    def action_confirm_clarification(self) -> None:
        if self._clarification_future and not self._clarification_future.done():
            self._clarification_future.set_result("Proceed with default.")

    def action_help(self) -> None:
        messages = self.query_one(MessageStreamWidget)
        messages.add_message(
            "system",
            "Keyboard shortcuts:\n"
            "  a = Approve  |  r = Reject  |  s = Skip\n"
            "  c = Confirm clarification  |  q = Quit  |  ? = Help",
        )
