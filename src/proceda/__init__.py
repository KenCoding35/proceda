"""Proceda: Turn SOPs into runnable agents with human oversight.

Usage:
    from proceda import Agent

    agent = Agent.from_path("./skills/my-skill")
    result = agent.run()
    print(result.status)
"""

from proceda.agent import Agent
from proceda.config import ProcedaConfig
from proceda.events import EventType, RunEvent
from proceda.human import (
    AutoApproveHumanInterface,
    HumanInterface,
    ScriptedHumanInterface,
    TerminalHumanInterface,
)
from proceda.session import RunResult, RunSession, RunStatus
from proceda.skill import Skill, SkillStep, StepMarker

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "AutoApproveHumanInterface",
    "EventType",
    "HumanInterface",
    "RunEvent",
    "RunResult",
    "RunSession",
    "RunStatus",
    "ScriptedHumanInterface",
    "Skill",
    "ProcedaConfig",
    "SkillStep",
    "StepMarker",
    "TerminalHumanInterface",
]
