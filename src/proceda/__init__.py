"""ABOUTME: Public API surface for the Proceda SDK.
ABOUTME: Re-exports core types: Agent, Skill, RunEvent, HumanInterface, RunSession, etc.
"""

from proceda.agent import Agent
from proceda.config import ProcedaConfig
from proceda.events import EventType, RunEvent
from proceda.execution import ContextManager, EmitFn, Executor, ToolExecutor
from proceda.human import (
    AutoApproveHumanInterface,
    HumanInterface,
    ScriptedHumanInterface,
    TerminalHumanInterface,
)
from proceda.session import RunResult, RunSession, RunStatus
from proceda.skill import Skill, SkillStep, StepMarker

__version__ = "0.1.1"

__all__ = [
    "Agent",
    "AutoApproveHumanInterface",
    "ContextManager",
    "EmitFn",
    "EventType",
    "Executor",
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
    "ToolExecutor",
]
