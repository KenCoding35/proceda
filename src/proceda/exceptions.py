"""ABOUTME: Proceda exception hierarchy.
ABOUTME: Defines all custom exceptions used throughout the runtime."""

from __future__ import annotations


class ProcedaError(Exception):
    """Base exception for all Proceda errors."""


class SkillParseError(ProcedaError):
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


class SkillLoadError(ProcedaError):
    """Raised when a skill file or directory cannot be loaded."""


class ConfigError(ProcedaError):
    """Raised when configuration is invalid or missing."""


class ExecutionError(ProcedaError):
    """Raised for runtime execution errors."""


class ToolAccessDeniedError(ProcedaError):
    """Raised when a tool call is blocked by allowlist/denylist policy."""

    def __init__(self, tool_name: str, reason: str = "denied by policy") -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' access denied: {reason}")


class ToolExecutionError(ProcedaError):
    """Raised when a tool call fails during execution."""

    def __init__(self, tool_name: str, message: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class LLMError(ProcedaError):
    """Raised for LLM-related errors."""


class LLMRateLimitError(LLMError):
    """Raised when the LLM API returns a rate limit error."""


class LLMTimeoutError(LLMError):
    """Raised when the LLM API call times out."""


class LLMAPIError(LLMError):
    """Raised when the LLM API returns an error."""


class SessionError(ProcedaError):
    """Raised for session state errors."""


class ApprovalRejectedError(ProcedaError):
    """Raised when a user rejects an approval request."""


class HumanInterfaceError(ProcedaError):
    """Raised for human interface communication errors."""


class ConversionError(ProcedaError):
    """Raised when an SOP cannot be converted to SKILL.md format."""
