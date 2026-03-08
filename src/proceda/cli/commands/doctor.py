"""ABOUTME: CLI `doctor` command that validates environment, config, and dependencies.
ABOUTME: Checks Python version, API keys, required packages, MCP apps, and run directory.
"""

from __future__ import annotations

import os
import sys

import typer
from rich.console import Console
from rich.table import Table

from proceda.config import CONFIG_FILENAMES, CONFIG_SEARCH_PATHS, ProcedaConfig

console = Console()


def doctor() -> None:
    """Check environment, configuration, and dependencies."""
    checks: list[tuple[str, str, str]] = []  # (name, status, detail)
    has_errors = False

    # Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(("Python version", "ok", py_version))

    # Config file
    config_found = False
    for search_dir in CONFIG_SEARCH_PATHS:
        for filename in CONFIG_FILENAMES:
            path = search_dir / filename
            if path.exists():
                checks.append(("Config file", "ok", str(path)))
                config_found = True
                break
        if config_found:
            break

    if not config_found:
        checks.append(("Config file", "warn", "No config file found (using defaults)"))

    # LLM API key
    api_key_vars = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    key_found = False
    for var in api_key_vars:
        if os.environ.get(var):
            checks.append(("LLM API key", "ok", f"${var} is set"))
            key_found = True
            break

    if not key_found:
        checks.append(
            (
                "LLM API key",
                "error",
                "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY",
            )
        )
        has_errors = True

    # Required packages
    packages = [
        ("litellm", "LLM integration"),
        ("typer", "CLI framework"),
        ("rich", "Terminal formatting"),
        ("textual", "TUI framework"),
        ("yaml", "Config parsing"),
        ("httpx", "HTTP client"),
    ]

    for pkg_name, purpose in packages:
        try:
            __import__(pkg_name)
            checks.append((f"Package: {pkg_name}", "ok", purpose))
        except ImportError:
            checks.append((f"Package: {pkg_name}", "error", f"Not installed ({purpose})"))
            has_errors = True

    # Run directory
    from pathlib import Path

    run_dir = Path(".proceda/runs")
    if run_dir.exists():
        run_count = len(list(run_dir.iterdir()))
        checks.append(("Run directory", "ok", f"{run_count} previous run(s)"))
    else:
        checks.append(("Run directory", "info", "Not yet created (will be created on first run)"))

    # MCP connectivity (if config has apps)
    try:
        cfg = ProcedaConfig.load()
        if cfg.apps:
            checks.append(("MCP apps configured", "ok", f"{len(cfg.apps)} app(s)"))
            for app in cfg.apps:
                checks.append(
                    (
                        f"  App: {app.name}",
                        "info",
                        f"{app.transport} transport",
                    )
                )
        else:
            checks.append(("MCP apps", "info", "No apps configured"))
    except Exception:
        checks.append(("MCP apps", "info", "No configuration to check"))

    # Render table
    table = Table(title="Proceda Doctor")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Detail")

    status_styles = {
        "ok": "[green]OK[/green]",
        "warn": "[yellow]WARN[/yellow]",
        "error": "[red]ERROR[/red]",
        "info": "[blue]INFO[/blue]",
    }

    for name, status, detail in checks:
        table.add_row(name, status_styles.get(status, status), detail)

    console.print(table)

    if has_errors:
        console.print("\n[red]Some checks failed. Fix the errors above to proceed.[/red]")
        raise typer.Exit(code=4)
    else:
        console.print("\n[green]All checks passed.[/green]")
