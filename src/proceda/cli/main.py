"""ABOUTME: Root CLI application built with Typer.
ABOUTME: Registers subcommands (run, dev, lint, replay, doctor).
"""

from __future__ import annotations

import typer

from proceda.cli.commands.dev import dev
from proceda.cli.commands.doctor import doctor
from proceda.cli.commands.lint import lint
from proceda.cli.commands.replay import replay
from proceda.cli.commands.run import run

app = typer.Typer(
    name="proceda",
    help="Proceda: Turn SOPs into runnable agents with human oversight.",
    no_args_is_help=True,
    add_completion=False,
)

# Register commands
app.command()(run)
app.command()(dev)
app.command()(lint)
app.command()(replay)
app.command()(doctor)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
