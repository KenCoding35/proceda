"""CLI `run` command: execute a skill interactively in the terminal."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

from proceda.config import ProcedaConfig
from proceda.events import EventType, RunEvent
from proceda.human import TerminalHumanInterface
from proceda.runtime import Runtime
from proceda.skills.loader import load_skill

console = Console()


class TerminalEventPrinter:
    """Prints events to the terminal in real-time."""

    def __init__(self, console: Console) -> None:
        self._console = console

    async def handle(self, event: RunEvent) -> None:
        t = event.type
        p = event.payload

        if t == EventType.RUN_CREATED:
            self._console.print(
                Panel(
                    f"[bold]{p.get('skill_name', '')}[/bold]\nSteps: {p.get('step_count', 0)}",
                    title="Proceda",
                    border_style="blue",
                )
            )

        elif t == EventType.STEP_STARTED:
            self._console.print(
                f"\n[bold cyan]>>> Step {p.get('step_index')}: {p.get('step_title')}[/bold cyan]"
            )

        elif t == EventType.STEP_COMPLETED:
            self._console.print(f"[green]    Step {p.get('step_index')} completed[/green]")

        elif t == EventType.STEP_SKIPPED:
            self._console.print(f"[yellow]    Step {p.get('step_index')} skipped[/yellow]")

        elif t == EventType.MESSAGE_ASSISTANT:
            content = p.get("content", "")
            if content:
                self._console.print(f"    {content}")

        elif t == EventType.TOOL_CALLED:
            self._console.print(f"    [cyan]Calling tool:[/cyan] {p.get('tool_name')}")

        elif t == EventType.TOOL_COMPLETED:
            result = str(p.get("result", ""))[:200]
            self._console.print(f"    [green]Result:[/green] {result}")

        elif t == EventType.TOOL_FAILED:
            self._console.print(f"    [red]Tool error:[/red] {p.get('error', '')}")

        elif t == EventType.RUN_COMPLETED:
            self._console.print("\n[bold green]Run completed successfully.[/bold green]")

        elif t == EventType.RUN_FAILED:
            self._console.print(f"\n[bold red]Run failed:[/bold red] {p.get('error', '')}")

        elif t == EventType.RUN_CANCELLED:
            self._console.print("\n[bold yellow]Run cancelled.[/bold yellow]")

        elif t == EventType.SUMMARY_GENERATED:
            self._console.print(f"    [dim]{p.get('summary', '')}[/dim]")


def run(
    path: str = typer.Argument(..., help="Path to a SKILL.md file or directory"),
    model: str | None = typer.Option(None, "--model", "-m", help="LLM model to use"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    var: list[str] | None = typer.Option(None, "--var", "-v", help="Variables as key=value"),
) -> None:
    """Run a skill interactively in the terminal."""
    try:
        # Load config
        cfg = ProcedaConfig.load(config)
        if model:
            cfg.llm.model = model

        # Parse variables
        variables: dict[str, str] = {}
        if var:
            for v in var:
                if "=" not in v:
                    console.print(f"[red]Invalid variable format: {v} (expected key=value)[/red]")
                    raise typer.Exit(code=2)
                key, value = v.split("=", 1)
                variables[key] = value

        # Load skill (pass LLM config for auto-structuring unformatted files)
        skill = load_skill(path, llm_config=cfg.llm)
        console.print(f"[dim]Loaded skill: {skill.name}[/dim]")

        # Run
        human = TerminalHumanInterface(console)
        runtime = Runtime(config=cfg, human=human)
        printer = TerminalEventPrinter(console)

        result = asyncio.run(runtime.run(skill, variables=variables, event_sinks=[printer]))

        # Print summary
        console.print()
        console.print(Panel(result.summary, title="Run Summary", border_style="blue"))

        if result.event_log_path:
            console.print(f"\n[dim]Event log: {result.event_log_path}[/dim]")

        # Exit code
        if result.status.value == "completed":
            raise typer.Exit(code=0)
        elif result.status.value == "cancelled":
            raise typer.Exit(code=3)
        else:
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
