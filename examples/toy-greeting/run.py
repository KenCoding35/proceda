# ABOUTME: Runs the toy-greeting skill using the Proceda Python API.
# ABOUTME: Demonstrates Agent.from_path() with config and event streaming.

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.panel import Panel

from proceda import Agent, RunEvent
from proceda.config import ProcedaConfig
from proceda.events import EventType
from proceda.human import TerminalHumanInterface

console = Console()


async def handle_event(event: RunEvent) -> None:
    t = event.type
    p = event.payload

    if t == EventType.STEP_STARTED:
        console.print(f"\n[bold cyan]>>> Step {p['step_index']}: {p['step_title']}[/bold cyan]")
    elif t == EventType.STEP_COMPLETED:
        console.print(f"[green]    Step {p['step_index']} completed[/green]")
    elif t == EventType.MESSAGE_ASSISTANT:
        if p.get("content"):
            console.print(f"    {p['content']}")
    elif t == EventType.TOOL_CALLED:
        console.print(f"    [cyan]Calling tool:[/cyan] {p.get('tool_name')}")
    elif t == EventType.TOOL_COMPLETED:
        console.print(f"    [green]Result:[/green] {str(p.get('result', ''))[:200]}")
    elif t == EventType.SUMMARY_GENERATED:
        console.print(f"    [dim]{p.get('summary', '')}[/dim]")


class EventPrinter:
    async def handle(self, event: RunEvent) -> None:
        await handle_event(event)


async def main() -> None:
    config = ProcedaConfig.load()
    human = TerminalHumanInterface(console)

    agent = Agent.from_path("./examples/toy-greeting", config=config, human=human)

    console.print(
        Panel(f"[bold]{agent.skill.name}[/bold]\n{agent.skill.description}", border_style="blue")
    )

    result = await agent.run_async(event_sinks=[EventPrinter()])

    console.print()
    console.print(Panel(result.summary, title="Run Summary", border_style="blue"))
    console.print(f"Status: {result.status.value}")


if __name__ == "__main__":
    asyncio.run(main())
