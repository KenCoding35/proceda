"""Replay engine: renders events from a saved run log."""

from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from skillrunner.events import EventType, RunEvent
from skillrunner.store.event_log import EventLogReader


class ReplayRenderer:
    """Renders replay events to the terminal."""

    def __init__(self, console: Console | None = None, speed: float = 1.0) -> None:
        self._console = console or Console()
        self._speed = speed

    def replay(self, run_dir: Path) -> bool:
        """Replay a run from its event log directory. Returns True if successful."""
        reader = EventLogReader(run_dir)

        if not reader.exists:
            self._console.print(f"[red]No event log found in {run_dir}[/red]")
            return False

        metadata = reader.read_metadata()
        if metadata:
            self._console.print(
                Panel(
                    f"Skill: {metadata.get('skill_name', 'unknown')}\n"
                    f"Run ID: {metadata.get('run_id', 'unknown')}\n"
                    f"Model: {metadata.get('model', 'unknown')}\n"
                    f"Created: {metadata.get('created_at', 'unknown')}",
                    title="Replay",
                    border_style="cyan",
                )
            )

        prev_time = None

        for event in reader.iter_events():
            # Simulate timing
            if prev_time and self._speed > 0:
                delta = (event.timestamp - prev_time).total_seconds()
                delay = min(delta / self._speed, 1.0)
                if delay > 0.01:
                    time.sleep(delay)
            prev_time = event.timestamp

            self._render_event(event)

        # Print summary if available
        summary = reader.read_summary()
        if summary:
            self._console.print()
            self._console.print(Panel(summary, title="Run Summary", border_style="green"))

        return True

    def _render_event(self, event: RunEvent) -> None:
        """Render a single event."""
        c = self._console
        t = event.type
        p = event.payload

        if t == EventType.RUN_CREATED:
            c.print(f"\n[bold]Run created[/bold]: {p.get('skill_name', '')}")

        elif t == EventType.RUN_STARTED:
            c.print("[green]Run started[/green]")

        elif t == EventType.STEP_STARTED:
            c.print(f"\n[bold cyan]Step {p.get('step_index')}: {p.get('step_title')}[/bold cyan]")

        elif t == EventType.STEP_COMPLETED:
            c.print(f"[green]Step {p.get('step_index')} completed[/green]")

        elif t == EventType.STEP_SKIPPED:
            c.print(f"[yellow]Step {p.get('step_index')} skipped: {p.get('reason', '')}[/yellow]")

        elif t == EventType.MESSAGE_ASSISTANT:
            content = p.get("content", "")
            if content:
                c.print(f"  [dim]Assistant:[/dim] {content[:200]}")

        elif t == EventType.MESSAGE_REASONING:
            content = p.get("content", "")
            if content:
                c.print(f"  [dim italic]Thinking: {content[:150]}...[/dim italic]")

        elif t == EventType.TOOL_CALLED:
            tool = p.get("tool_name")
            args = _fmt_args(p.get("arguments", {}))
            c.print(f"  [cyan]Tool call:[/cyan] {tool}({args})")

        elif t == EventType.TOOL_COMPLETED:
            result = p.get("result", "")
            c.print(f"  [green]Tool result:[/green] {str(result)[:100]}")

        elif t == EventType.TOOL_FAILED:
            c.print(f"  [red]Tool failed:[/red] {p.get('error', '')}")

        elif t == EventType.APPROVAL_REQUESTED:
            atype = p.get("approval_type")
            step = p.get("step_index")
            c.print(f"  [yellow]Approval requested:[/yellow] {atype} for step {step}")

        elif t == EventType.APPROVAL_RESPONDED:
            c.print(f"  [yellow]Approval:[/yellow] {p.get('decision')}")

        elif t == EventType.CLARIFICATION_REQUESTED:
            c.print(f"  [blue]Clarification:[/blue] {p.get('question')}")

        elif t == EventType.CLARIFICATION_RESPONDED:
            c.print(f"  [blue]Answer:[/blue] {p.get('answer')}")

        elif t == EventType.RUN_COMPLETED:
            c.print("\n[bold green]Run completed[/bold green]")

        elif t == EventType.RUN_FAILED:
            c.print(f"\n[bold red]Run failed:[/bold red] {p.get('error', '')}")

        elif t == EventType.RUN_CANCELLED:
            c.print("\n[bold yellow]Run cancelled[/bold yellow]")

        elif t == EventType.SUMMARY_GENERATED:
            c.print(f"  [dim]Summary:[/dim] {p.get('summary', '')}")

        elif t == EventType.STATUS_CHANGED:
            pass  # Don't clutter replay with status changes


def _fmt_args(args: dict) -> str:
    """Format tool arguments for display."""
    if not args:
        return ""
    parts = [f"{k}={repr(v)}" for k, v in list(args.items())[:3]]
    result = ", ".join(parts)
    if len(args) > 3:
        result += ", ..."
    return result
