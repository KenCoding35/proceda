"""MCP client transports: stdio and HTTP."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from abc import ABC, abstractmethod
from typing import Any

from skillrunner.exceptions import ToolExecutionError
from skillrunner.mcp.models import MCPApp, MCPArtifact, MCPTool, MCPToolResult

logger = logging.getLogger(__name__)


class MCPClient(ABC):
    """Base class for MCP transport clients."""

    def __init__(self, app: MCPApp) -> None:
        self.app = app

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the MCP server."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""

    @abstractmethod
    async def list_tools(self) -> list[MCPTool]:
        """Discover available tools from the server."""

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Execute a tool and return the result."""


class StdioMCPClient(MCPClient):
    """MCP client over stdio (subprocess)."""

    def __init__(self, app: MCPApp) -> None:
        super().__init__(app)
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0

    async def connect(self) -> None:
        if not self.app.command:
            raise ToolExecutionError(self.app.name, "No command specified for stdio transport")

        env = os.environ.copy()
        if self.app.env:
            env.update(self.app.env)

        self._process = await asyncio.create_subprocess_exec(
            *self.app.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        self.app.connected = True

        # Send initialize request
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "skillrunner", "version": "0.1.0"},
        })

    async def disconnect(self) -> None:
        if self._process:
            try:
                self._process.stdin.close()  # type: ignore
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except (asyncio.TimeoutError, ProcessLookupError):
                self._process.kill()
            self._process = None
            self.app.connected = False

    async def list_tools(self) -> list[MCPTool]:
        result = await self._send_request("tools/list", {})
        tools = []
        for tool_data in result.get("tools", []):
            tools.append(
                MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    app_name=self.app.name,
                )
            )
        self.app.tools = tools
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        try:
            result = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments,
            })
            return self._parse_result(tool_name, result)
        except Exception as e:
            return MCPToolResult(
                tool_name=tool_name,
                content=str(e),
                is_error=True,
            )

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise ToolExecutionError(self.app.name, "Not connected")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        line = json.dumps(request) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

        response_line = await asyncio.wait_for(
            self._process.stdout.readline(),
            timeout=30.0,
        )

        if not response_line:
            raise ToolExecutionError(self.app.name, "No response from MCP server")

        response = json.loads(response_line)

        if "error" in response:
            error = response["error"]
            raise ToolExecutionError(
                self.app.name,
                f"{error.get('message', 'Unknown error')} (code: {error.get('code')})",
            )

        return response.get("result", {})

    def _parse_result(self, tool_name: str, result: dict[str, Any]) -> MCPToolResult:
        content_parts = result.get("content", [])
        text_parts = []
        artifacts = []

        for part in content_parts:
            if part.get("type") == "text":
                text_parts.append(part.get("text", ""))
            elif part.get("type") == "resource":
                artifacts.append(
                    MCPArtifact(
                        content_type=part.get("mimeType", "application/octet-stream"),
                        content=part.get("text", part.get("data", "")),
                        name=part.get("name"),
                    )
                )

        return MCPToolResult(
            tool_name=tool_name,
            content="\n".join(text_parts) if text_parts else str(result),
            is_error=result.get("isError", False),
            raw_content=content_parts,
            artifacts=artifacts if artifacts else None,
        )


class HTTPMCPClient(MCPClient):
    """MCP client over HTTP."""

    def __init__(self, app: MCPApp) -> None:
        super().__init__(app)
        self._client: Any = None

    async def connect(self) -> None:
        import httpx

        if not self.app.url:
            raise ToolExecutionError(self.app.name, "No URL specified for HTTP transport")
        self._client = httpx.AsyncClient(base_url=self.app.url, timeout=30.0)
        self.app.connected = True

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            self.app.connected = False

    async def list_tools(self) -> list[MCPTool]:
        response = await self._post("tools/list", {})
        tools = []
        for tool_data in response.get("tools", []):
            tools.append(
                MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    app_name=self.app.name,
                )
            )
        self.app.tools = tools
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        try:
            result = await self._post("tools/call", {
                "name": tool_name,
                "arguments": arguments,
            })
            content_parts = result.get("content", [])
            text = "\n".join(p.get("text", "") for p in content_parts if p.get("type") == "text")
            return MCPToolResult(
                tool_name=tool_name,
                content=text or str(result),
                is_error=result.get("isError", False),
                raw_content=content_parts,
            )
        except Exception as e:
            return MCPToolResult(
                tool_name=tool_name,
                content=str(e),
                is_error=True,
            )

    async def _post(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            raise ToolExecutionError(self.app.name, "Not connected")

        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }

        response = await self._client.post("/", json=request)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            error = data["error"]
            raise ToolExecutionError(
                self.app.name,
                f"{error.get('message', 'Unknown error')} (code: {error.get('code')})",
            )

        return data.get("result", {})
