"""TUI widgets for the SkillRunner dev mode interface."""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.widgets import Static, RichLog

from skillrunner.skill import Skill


class SkillHeaderWidget(Static):
    """Displays skill name and description."""

    def __init__(self, skill: Skill, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._skill = skill

    def on_mount(self) -> None:
        self.update(
            Text.from_markup(
                f"[bold]{self._skill.name}[/bold]\n"
                f"[dim]{self._skill.description}[/dim]\n"
                f"[dim]Steps: {self._skill.step_count}[/dim]"
            )
        )


class StepListWidget(Static):
    """Displays the list of steps with status indicators."""

    def __init__(self, skill: Skill, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._skill = skill
        self._active_step: int = 0
        self._completed: set[int] = set()
        self._skipped: set[int] = set()

    def on_mount(self) -> None:
        self._render_steps()

    def set_active_step(self, index: int) -> None:
        self._active_step = index
        self._render_steps()

    def mark_completed(self, index: int) -> None:
        self._completed.add(index)
        self._render_steps()

    def mark_skipped(self, index: int) -> None:
        self._skipped.add(index)
        self._render_steps()

    def _render_steps(self) -> None:
        lines = ["[bold]Steps[/bold]\n"]
        for step in self._skill.steps:
            if step.index in self._completed:
                icon = "[green]v[/green]"
            elif step.index in self._skipped:
                icon = "[yellow]-[/yellow]"
            elif step.index == self._active_step:
                icon = "[cyan]>[/cyan]"
            else:
                icon = "[dim]o[/dim]"

            markers = ""
            if step.requires_pre_approval:
                markers = " [yellow]*[/yellow]"
            elif step.requires_post_approval:
                markers = " [yellow]*[/yellow]"

            style = "bold" if step.index == self._active_step else ""
            lines.append(f"  {icon} [{style}]{step.index}. {step.title}[/{style}]{markers}")

        self.update(Text.from_markup("\n".join(lines)))


class MessageStreamWidget(RichLog):
    """Displays the live message stream."""

    def add_message(self, role: str, content: str) -> None:
        if not content:
            return

        styles = {
            "assistant": "[white]",
            "system": "[yellow]",
            "reasoning": "[dim italic]",
            "summary": "[green]",
        }

        style = styles.get(role, "")
        end_style = style.replace("[", "[/") if style else ""

        prefix = {
            "assistant": "Assistant",
            "system": "System",
            "reasoning": "Thinking",
            "summary": "Summary",
        }.get(role, role.capitalize())

        self.write(Text.from_markup(f"{style}{prefix}: {content}{end_style}"))


class ToolActivityWidget(RichLog):
    """Displays tool call activity."""

    def add_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in list(arguments.items())[:3])
        self.write(Text.from_markup(f"[cyan]CALL[/cyan] {tool_name}({args_str})"))

    def add_result(self, tool_name: str, result: str, success: bool = True) -> None:
        if success:
            self.write(Text.from_markup(f"[green]OK[/green] {tool_name}: {str(result)[:100]}"))
        else:
            self.write(Text.from_markup(f"[red]ERR[/red] {tool_name}: {str(result)[:100]}"))


class StatusBarWidget(Static):
    """Displays current status in the footer area."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._status = "created"
        self._hint = ""

    def on_mount(self) -> None:
        self._render()

    def update_status(self, status: str) -> None:
        self._status = status
        self._hint = ""
        self._render()

    def show_approval_hint(self) -> None:
        self._hint = "  [a]Approve  [r]Reject  [s]Skip"
        self._render()

    def _render(self) -> None:
        status_colors = {
            "created": "dim",
            "running": "green",
            "awaiting_approval": "yellow",
            "awaiting_input": "blue",
            "completed": "bold green",
            "failed": "bold red",
            "cancelled": "bold yellow",
        }
        color = status_colors.get(self._status, "white")
        self.update(
            Text.from_markup(
                f"[{color}]Status: {self._status}[/{color}]{self._hint}"
            )
        )
