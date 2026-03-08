"""ABOUTME: Data models for MCP tools, tool results, artifacts, and app configurations.
ABOUTME: Defines the core types used throughout the MCP integration layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPTool:
    """A tool exposed by an MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    app_name: str = ""

    @property
    def qualified_name(self) -> str:
        """Full name including app prefix: app__tool."""
        if self.app_name:
            return f"{self.app_name}__{self.name}"
        return self.name

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI-compatible tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.qualified_name,
                "description": self.description,
                "parameters": self.input_schema or {"type": "object", "properties": {}},
            },
        }


@dataclass
class MCPToolResult:
    """Result from executing an MCP tool."""

    tool_name: str
    content: str
    is_error: bool = False
    raw_content: list[dict[str, Any]] | None = None
    artifacts: list[MCPArtifact] | None = None


@dataclass
class MCPArtifact:
    """An artifact returned by an MCP tool (e.g., HTML, file)."""

    content_type: str
    content: str
    name: str | None = None


@dataclass
class MCPApp:
    """An MCP application (tool server) configuration."""

    name: str
    description: str
    transport: str  # "stdio" or "http"
    command: list[str] | None = None
    url: str | None = None
    env: dict[str, str] | None = None
    tools: list[MCPTool] = field(default_factory=list)
    connected: bool = False
