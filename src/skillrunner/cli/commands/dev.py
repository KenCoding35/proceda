"""CLI `dev` command: run a skill in full-screen TUI mode."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()


def dev(
    path: str = typer.Argument(..., help="Path to a SKILL.md file or directory"),
    model: str | None = typer.Option(None, "--model", "-m", help="LLM model to use"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    var: list[str] | None = typer.Option(None, "--var", "-v", help="Variables as key=value"),
) -> None:
    """Run a skill in full-screen TUI dev mode."""
    try:
        from skillrunner.config import SkillRunnerConfig
        from skillrunner.skills.loader import load_skill
        from skillrunner.tui.app import SkillRunnerApp

        # Load config
        cfg = SkillRunnerConfig.load(config)
        if model:
            cfg.llm.model = model

        # Parse variables
        variables: dict[str, str] = {}
        if var:
            for v in var:
                if "=" not in v:
                    console.print(f"[red]Invalid variable format: {v}[/red]")
                    raise typer.Exit(code=2)
                key, value = v.split("=", 1)
                variables[key] = value

        # Load skill
        skill = load_skill(path)

        # Launch TUI
        app = SkillRunnerApp(skill=skill, config=cfg, variables=variables)
        app.run()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
