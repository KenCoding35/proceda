"""SkillRunner exception hierarchy."""

from __future__ import annotations


class SkillRunnerError(Exception):
    """Base exception for all SkillRunner errors."""


class SkillParseError(SkillRunnerError):
    """Raised when a SKILL.md file cannot be parsed."""

    def __init__(self, message: str, line: int | None = None, path: str | None = None) -> None:
        self.line = line
        self.path = path
        detail = message
        if path:
            detail = f"{path}: {detail}"
        if line is not None:
            detail = f"{detail} (line {line})"
        super().__init__(detail)


class SkillLoadError(SkillRunnerError):
    """Raised when a skill file or directory cannot be loaded."""


class ConfigError(SkillRunnerError):
    """Raised when configuration is invalid or missing."""


class ExecutionError(SkillRunnerError):
    """Raised for runtime execution errors."""


class ToolAccessDeniedError(SkillRunnerError):
    """Raised when a tool call is blocked by allowlist/denylist policy."""

    def __init__(self, tool_name: str, reason: str = "denied by policy") -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' access denied: {reason}")


class ToolExecutionError(SkillRunnerError):
    """Raised when a tool call fails during execution."""

    def __init__(self, tool_name: str, message: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class LLMError(SkillRunnerError):
    """Raised for LLM-related errors."""


class SessionError(SkillRunnerError):
    """Raised for session state errors."""


class ApprovalRejectedError(SkillRunnerError):
    """Raised when a user rejects an approval request."""


class HumanInterfaceError(SkillRunnerError):
    """Raised for human interface communication errors."""
