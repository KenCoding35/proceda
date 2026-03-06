"""CLI root: the `skillrunner` command."""

from __future__ import annotations

import sys

import typer

from skillrunner.cli.commands.dev import dev
from skillrunner.cli.commands.doctor import doctor
from skillrunner.cli.commands.lint import lint
from skillrunner.cli.commands.replay import replay
from skillrunner.cli.commands.run import run

app = typer.Typer(
    name="skillrunner",
    help="SkillRunner: Turn SOPs into runnable agents with human oversight.",
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
