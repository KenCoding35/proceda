"""ABOUTME: CLI `lint` command that validates a SKILL.md file.
ABOUTME: Reports errors and warnings from the skill parser's lint_skill function.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from proceda.skills.loader import SKILL_FILENAME
from proceda.skills.parser import lint_skill

console = Console()


def lint(
    path: str = typer.Argument(..., help="Path to a SKILL.md file or directory"),
) -> None:
    """Validate a skill definition and report warnings and errors."""
    try:
        resolved = Path(path).resolve()

        if resolved.is_dir():
            skill_file = resolved / SKILL_FILENAME
        elif resolved.is_file():
            skill_file = resolved
        else:
            console.print(f"[red]Path does not exist: {resolved}[/red]")
            raise typer.Exit(code=2)

        if not skill_file.exists():
            console.print(f"[red]No {SKILL_FILENAME} found at: {skill_file}[/red]")
            raise typer.Exit(code=2)

        content = skill_file.read_text(encoding="utf-8")
        result = lint_skill(content, path=skill_file)

        # Print errors
        for issue in result.errors:
            line_info = f" (line {issue.line})" if issue.line else ""
            console.print(f"[red]ERROR{line_info}:[/red] {issue.message}")

        # Print warnings
        for issue in result.warnings:
            line_info = f" (line {issue.line})" if issue.line else ""
            console.print(f"[yellow]WARNING{line_info}:[/yellow] {issue.message}")

        if result.ok and not result.has_warnings:
            console.print(f"[green]Skill '{result.skill.name}' is valid.[/green]")  # type: ignore
            console.print(f"  Steps: {result.skill.step_count}")  # type: ignore
            if result.skill.required_tools:  # type: ignore
                console.print(f"  Required tools: {', '.join(result.skill.required_tools)}")  # type: ignore
        elif result.ok:
            console.print(f"[green]Skill is valid[/green] with {len(result.warnings)} warning(s).")

        if not result.ok:
            raise typer.Exit(code=2)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=2)
