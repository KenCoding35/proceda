"""ABOUTME: CLI `replay` command that replays a previous run from saved event logs.
ABOUTME: Resolves a run by ID or path and renders it via ReplayRenderer.
"""

from __future__ import annotations

import typer
from rich.console import Console

from proceda.replay import ReplayRenderer
from proceda.store.event_log import RunDirectoryManager

console = Console()


def replay(
    run_id_or_path: str = typer.Argument(..., help="Run ID, run directory path, or partial match"),
    run_dir: str | None = typer.Option(None, "--run-dir", help="Base run directory"),
) -> None:
    """Replay a previous run from event logs."""
    try:
        manager = RunDirectoryManager(run_dir or ".proceda/runs")
        found = manager.find_run(run_id_or_path)

        if not found:
            console.print(f"[red]Run not found: {run_id_or_path}[/red]")
            console.print("\n[dim]Available runs:[/dim]")
            for d in manager.list_runs()[:10]:
                console.print(f"  {d.name}")
            raise typer.Exit(code=2)

        renderer = ReplayRenderer(console=console)
        success = renderer.replay(found)

        if not success:
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
