"""Agent: high-level public API for loading and running skills."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from proceda.config import ProcedaConfig
from proceda.events import RunEvent
from proceda.human import AutoApproveHumanInterface, HumanInterface
from proceda.runtime import RunHandle, Runtime
from proceda.session import RunResult
from proceda.skill import Skill
from proceda.skills.loader import load_skill


class Agent:
    """High-level agent wrapper around a skill + runtime configuration.

    Usage:
        agent = Agent.from_path("./skills/expense-processing")
        result = agent.run()
        print(result.status)
    """

    def __init__(
        self,
        skill: Skill,
        config: ProcedaConfig | None = None,
        human: HumanInterface | None = None,
    ) -> None:
        self._skill = skill
        self._config = config or ProcedaConfig()
        self._human = human or AutoApproveHumanInterface()

    @staticmethod
    def from_path(
        path: str | Path,
        config: ProcedaConfig | None = None,
        human: HumanInterface | None = None,
    ) -> Agent:
        """Create an agent from a skill file or directory path."""
        skill = load_skill(path)
        return Agent(skill=skill, config=config, human=human)

    @property
    def skill(self) -> Skill:
        return self._skill

    @property
    def config(self) -> ProcedaConfig:
        return self._config

    def run(
        self,
        variables: dict[str, str] | None = None,
        event_sinks: list[Any] | None = None,
    ) -> RunResult:
        """Run the skill synchronously and return the result."""
        return asyncio.run(self.run_async(variables=variables, event_sinks=event_sinks))

    async def run_async(
        self,
        variables: dict[str, str] | None = None,
        event_sinks: list[Any] | None = None,
    ) -> RunResult:
        """Run the skill asynchronously and return the result."""
        runtime = Runtime(config=self._config, human=self._human)
        return await runtime.run(self._skill, variables=variables, event_sinks=event_sinks)

    async def create_session(
        self,
        variables: dict[str, str] | None = None,
        event_sinks: list[Any] | None = None,
    ) -> RunHandle:
        """Create a session and return a handle for event-driven usage."""
        runtime = Runtime(config=self._config, human=self._human)
        return await runtime.start(self._skill, variables=variables, event_sinks=event_sinks)

    async def run_stream(
        self,
        variables: dict[str, str] | None = None,
    ) -> AsyncIterator[RunEvent]:
        """Run the skill and yield events as they occur."""
        handle = await self.create_session(variables=variables)
        async for event in handle.events():
            yield event
