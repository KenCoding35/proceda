"""ABOUTME: Public API surface for the Proceda SDK.
ABOUTME: Re-exports core types: Agent, Skill, RunEvent, HumanInterface, RunSession, etc.
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
