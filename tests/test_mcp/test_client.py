"""ABOUTME: Tests for MCP client transports (StdioMCPClient and HTTPMCPClient).
ABOUTME: Validates JSON-RPC communication, tool discovery, and error handling."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from proceda.exceptions import ToolExecutionError
from proceda.mcp.client import HTTPMCPClient, StdioMCPClient
from proceda.mcp.models import MCPApp


def _make_app(transport: str = "stdio", **kwargs) -> MCPApp:
    return MCPApp(name="test-app", description="test app", transport=transport, **kwargs)


def _jsonrpc_response(result: dict, id: int = 1) -> bytes:
    return (json.dumps({"jsonrpc": "2.0", "id": id, "result": result}) + "\n").encode()


def _jsonrpc_error(code: int, message: str, id: int = 1) -> bytes:
    return (
        json.dumps({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}) + "\n"
    ).encode()


# ---------------------------------------------------------------------------
# StdioMCPClient
# ---------------------------------------------------------------------------


class TestStdioMCPClientConnect:
    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        app = _make_app(command=["echo", "hello"])
        client = StdioMCPClient(app)

        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=_jsonrpc_response({"protocolVersion": "2024-11-05"})
        )

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)):
            await client.connect()

        assert app.connected is True
        assert client._process is mock_process

    @pytest.mark.asyncio
    async def test_connect_no_command_raises(self) -> None:
        app = _make_app(command=None)
        client = StdioMCPClient(app)

        with pytest.raises(ToolExecutionError, match="No command specified"):
            await client.connect()


class TestStdioMCPClientDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_kills_on_timeout(self) -> None:
        app = _make_app(command=["sleep", "999"])
        client = StdioMCPClient(app)

        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.close = MagicMock()
        mock_process.wait = AsyncMock(side_effect=TimeoutError)
        mock_process.kill = MagicMock()
        client._process = mock_process
        app.connected = True

        await client.disconnect()

        mock_process.kill.assert_called_once()
        assert client._process is None
        assert app.connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self) -> None:
        app = _make_app()
        client = StdioMCPClient(app)

        # Should be a no-op
        await client.disconnect()
        assert app.connected is False


class TestStdioMCPClientListTools:
    @pytest.mark.asyncio
    async def test_list_tools_parses_response(self) -> None:
        app = _make_app(command=["fake"])
        client = StdioMCPClient(app)

        tools_response = {
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read a file",
                    "inputSchema": {"type": "object"},
                },
                {"name": "write_file", "description": "Write a file"},
            ]
        }

        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=_jsonrpc_response(tools_response))
        client._process = mock_process

        tools = await client.list_tools()

        assert len(tools) == 2
        assert tools[0].name == "read_file"
        assert tools[0].description == "Read a file"
        assert tools[0].input_schema == {"type": "object"}
        assert tools[0].app_name == "test-app"
        assert tools[1].name == "write_file"
        assert tools[1].description == "Write a file"
        assert app.tools == tools


class TestStdioMCPClientCallTool:
    @pytest.mark.asyncio
    async def test_call_tool_text_content(self) -> None:
        app = _make_app(command=["fake"])
        client = StdioMCPClient(app)

        tool_result = {
            "content": [{"type": "text", "text": "file contents here"}],
        }

        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=_jsonrpc_response(tool_result))
        client._process = mock_process

        result = await client.call_tool("read_file", {"path": "/tmp/test"})

        assert result.tool_name == "read_file"
        assert result.content == "file contents here"
        assert result.is_error is False
        assert result.artifacts is None

    @pytest.mark.asyncio
    async def test_call_tool_with_artifacts(self) -> None:
        app = _make_app(command=["fake"])
        client = StdioMCPClient(app)

        tool_result = {
            "content": [
                {"type": "text", "text": "summary"},
                {
                    "type": "resource",
                    "mimeType": "image/png",
                    "data": "base64data",
                    "name": "screenshot.png",
                },
            ],
        }

        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=_jsonrpc_response(tool_result))
        client._process = mock_process

        result = await client.call_tool("screenshot", {})

        assert result.content == "summary"
        assert result.artifacts is not None
        assert len(result.artifacts) == 1
        assert result.artifacts[0].content_type == "image/png"
        assert result.artifacts[0].content == "base64data"
        assert result.artifacts[0].name == "screenshot.png"

    @pytest.mark.asyncio
    async def test_call_tool_server_error_response(self) -> None:
        app = _make_app(command=["fake"])
        client = StdioMCPClient(app)

        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = AsyncMock(
            return_value=_jsonrpc_error(-32600, "Invalid request")
        )
        client._process = mock_process

        result = await client.call_tool("bad_tool", {})

        assert result.is_error is True
        assert "Invalid request" in result.content

    @pytest.mark.asyncio
    async def test_call_tool_exception_returns_error_result(self) -> None:
        app = _make_app(command=["fake"])
        client = StdioMCPClient(app)
        # No process set, so _send_request will raise
        result = await client.call_tool("any_tool", {})

        assert result.is_error is True
        assert result.tool_name == "any_tool"

    @pytest.mark.asyncio
    async def test_call_tool_is_error_flag_from_result(self) -> None:
        app = _make_app(command=["fake"])
        client = StdioMCPClient(app)

        tool_result = {
            "content": [{"type": "text", "text": "something went wrong"}],
            "isError": True,
        }

        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=_jsonrpc_response(tool_result))
        client._process = mock_process

        result = await client.call_tool("failing_tool", {})

        assert result.is_error is True
        assert result.content == "something went wrong"


class TestStdioMCPClientSendRequest:
    @pytest.mark.asyncio
    async def test_send_request_not_connected_raises(self) -> None:
        app = _make_app(command=["fake"])
        client = StdioMCPClient(app)

        with pytest.raises(ToolExecutionError, match="Not connected"):
            await client._send_request("tools/list", {})

    @pytest.mark.asyncio
    async def test_send_request_empty_response_raises(self) -> None:
        app = _make_app(command=["fake"])
        client = StdioMCPClient(app)

        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        client._process = mock_process

        with pytest.raises(ToolExecutionError, match="No response"):
            await client._send_request("tools/list", {})


class TestStdioMCPClientParseResult:
    def test_parse_text_and_artifacts(self) -> None:
        app = _make_app()
        client = StdioMCPClient(app)

        result = client._parse_result(
            "my_tool",
            {
                "content": [
                    {"type": "text", "text": "line1"},
                    {"type": "text", "text": "line2"},
                    {
                        "type": "resource",
                        "mimeType": "text/plain",
                        "text": "file data",
                        "name": "f.txt",
                    },
                ]
            },
        )

        assert result.tool_name == "my_tool"
        assert result.content == "line1\nline2"
        assert result.artifacts is not None
        assert len(result.artifacts) == 1
        assert result.artifacts[0].content == "file data"

    def test_parse_no_text_falls_back_to_str(self) -> None:
        app = _make_app()
        client = StdioMCPClient(app)

        raw = {"content": [{"type": "resource", "mimeType": "image/png", "data": "abc"}]}
        result = client._parse_result("tool", raw)

        # No text parts, so content should be str(result)
        assert result.content == str(raw)


# ---------------------------------------------------------------------------
# HTTPMCPClient
# ---------------------------------------------------------------------------


class TestHTTPMCPClientConnect:
    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        app = _make_app(transport="http", url="http://localhost:8080")
        client = HTTPMCPClient(app)

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_instance = MagicMock()
            mock_async_client.return_value = mock_instance
            await client.connect()

        assert app.connected is True
        assert client._client is mock_instance

    @pytest.mark.asyncio
    async def test_connect_no_url_raises(self) -> None:
        app = _make_app(transport="http", url=None)
        client = HTTPMCPClient(app)

        with pytest.raises(ToolExecutionError, match="No URL specified"):
            await client.connect()


class TestHTTPMCPClientDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self) -> None:
        app = _make_app(transport="http", url="http://localhost:8080")
        client = HTTPMCPClient(app)
        mock_http = AsyncMock()
        client._client = mock_http
        app.connected = True

        await client.disconnect()

        mock_http.aclose.assert_awaited_once()
        assert client._client is None
        assert app.connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self) -> None:
        app = _make_app(transport="http")
        client = HTTPMCPClient(app)

        await client.disconnect()
        assert app.connected is False


class TestHTTPMCPClientListTools:
    @pytest.mark.asyncio
    async def test_list_tools_parses_response(self) -> None:
        app = _make_app(transport="http", url="http://localhost:8080")
        client = HTTPMCPClient(app)

        tools_payload = {
            "tools": [
                {
                    "name": "search",
                    "description": "Search things",
                    "inputSchema": {"type": "object"},
                },
            ]
        }
        mock_response = MagicMock()
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "x", "result": tools_payload}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        client._client = mock_http

        tools = await client.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "search"
        assert tools[0].app_name == "test-app"
        assert app.tools == tools


class TestHTTPMCPClientCallTool:
    @pytest.mark.asyncio
    async def test_call_tool_success(self) -> None:
        app = _make_app(transport="http", url="http://localhost:8080")
        client = HTTPMCPClient(app)

        result_payload = {
            "content": [{"type": "text", "text": "result text"}],
        }
        mock_response = MagicMock()
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "x", "result": result_payload}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        client._client = mock_http

        result = await client.call_tool("search", {"query": "test"})

        assert result.tool_name == "search"
        assert result.content == "result text"
        assert result.is_error is False

    @pytest.mark.asyncio
    async def test_call_tool_error_response(self) -> None:
        app = _make_app(transport="http", url="http://localhost:8080")
        client = HTTPMCPClient(app)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "x",
            "error": {"code": -32600, "message": "Bad request"},
        }
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        client._client = mock_http

        result = await client.call_tool("bad_tool", {})

        assert result.is_error is True
        assert "Bad request" in result.content

    @pytest.mark.asyncio
    async def test_call_tool_exception_returns_error_result(self) -> None:
        app = _make_app(transport="http")
        client = HTTPMCPClient(app)
        # No client set, so _post will raise
        result = await client.call_tool("any_tool", {})

        assert result.is_error is True
        assert result.tool_name == "any_tool"


class TestHTTPMCPClientPost:
    @pytest.mark.asyncio
    async def test_post_not_connected_raises(self) -> None:
        app = _make_app(transport="http")
        client = HTTPMCPClient(app)

        with pytest.raises(ToolExecutionError, match="Not connected"):
            await client._post("tools/list", {})

    @pytest.mark.asyncio
    async def test_post_jsonrpc_error_raises(self) -> None:
        app = _make_app(transport="http", url="http://localhost:8080")
        client = HTTPMCPClient(app)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "x",
            "error": {"code": -32601, "message": "Method not found"},
        }
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        client._client = mock_http

        with pytest.raises(ToolExecutionError, match="Method not found"):
            await client._post("nonexistent/method", {})
