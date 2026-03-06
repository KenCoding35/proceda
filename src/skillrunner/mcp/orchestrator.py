"""MCP orchestrator: manages multiple MCP apps and enforces access policies."""

from __future__ import annotations

import fnmatch
import logging
from typing import Any

from skillrunner.config import AppConfig, SecurityConfig
from skillrunner.exceptions import ToolAccessDeniedError, ToolExecutionError
from skillrunner.mcp.client import HTTPMCPClient, MCPClient, StdioMCPClient
from skillrunner.mcp.models import MCPApp, MCPTool, MCPToolResult

logger = logging.getLogger(__name__)


class MCPOrchestrator:
    """Manages MCP app connections, tool discovery, and access policies."""

    def __init__(
        self,
        app_configs: list[AppConfig] | None = None,
        security: SecurityConfig | None = None,
        required_tools: list[str] | None = None,
    ) -> None:
        self._apps: dict[str, MCPApp] = {}
        self._clients: dict[str, MCPClient] = {}
        self._tools: dict[str, MCPTool] = {}
        self._security = security or SecurityConfig()
        self._required_tools = required_tools
        self._app_configs = app_configs or []

    async def connect_all(self) -> None:
        """Connect to all configured MCP apps."""
        for app_config in self._app_configs:
            app = MCPApp(
                name=app_config.name,
                description=app_config.description,
                transport=app_config.transport,
                command=app_config.command,
                url=app_config.url,
                env=app_config.env,
            )
            self._apps[app.name] = app

            client = self._create_client(app)
            self._clients[app.name] = client

            try:
                await client.connect()
                tools = await client.list_tools()
                for tool in tools:
                    self._tools[tool.qualified_name] = tool
                logger.info(f"Connected to MCP app '{app.name}' ({len(tools)} tools)")
            except Exception as e:
                logger.warning(f"Failed to connect to MCP app '{app.name}': {e}")

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP apps."""
        for name, client in self._clients.items():
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting from '{name}': {e}")
        self._clients.clear()

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get OpenAI-compatible schemas for all available tools."""
        schemas = []
        for tool in self._tools.values():
            if self._is_tool_allowed(tool.qualified_name):
                schemas.append(tool.to_openai_schema())
        return schemas

    def get_available_tools(self) -> list[MCPTool]:
        """Get list of all available (and allowed) tools."""
        return [t for t in self._tools.values() if self._is_tool_allowed(t.qualified_name)]

    async def call_tool(self, qualified_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Execute a tool call, enforcing access policies."""
        if not self._is_tool_allowed(qualified_name):
            raise ToolAccessDeniedError(qualified_name)

        tool = self._tools.get(qualified_name)
        if not tool:
            raise ToolExecutionError(qualified_name, f"Tool not found: {qualified_name}")

        client = self._clients.get(tool.app_name)
        if not client:
            raise ToolExecutionError(qualified_name, f"No client for app '{tool.app_name}'")

        # Use the local tool name (without app prefix) for the MCP call
        return await client.call_tool(tool.name, arguments)

    def resolve_tool(self, name: str) -> MCPTool | None:
        """Look up a tool by qualified or unqualified name."""
        if name in self._tools:
            return self._tools[name]
        # Try unqualified name match
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None

    def check_required_tools(self) -> list[str]:
        """Return list of required tools that are not available."""
        if not self._required_tools:
            return []
        available = set(self._tools.keys())
        return [t for t in self._required_tools if t not in available]

    def _is_tool_allowed(self, qualified_name: str) -> bool:
        """Check if a tool is allowed by denylist and required_tools policies."""
        # Check denylist
        for pattern in self._security.tool_denylist:
            if fnmatch.fnmatch(qualified_name, pattern):
                return False

        # Check required_tools allowlist (if declared)
        if self._required_tools is not None:
            return qualified_name in self._required_tools

        return True

    def _create_client(self, app: MCPApp) -> MCPClient:
        if app.transport == "stdio":
            return StdioMCPClient(app)
        elif app.transport == "http":
            return HTTPMCPClient(app)
        else:
            raise ToolExecutionError(app.name, f"Unknown transport: {app.transport}")
