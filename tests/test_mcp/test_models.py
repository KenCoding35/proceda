"""Tests for MCP data models."""

from __future__ import annotations

from proceda.mcp.models import MCPApp, MCPArtifact, MCPTool, MCPToolResult


class TestMCPTool:
    def test_qualified_name_with_app(self) -> None:
        tool = MCPTool(name="extract", description="Extract data", app_name="receipts")
        assert tool.qualified_name == "receipts__extract"

    def test_qualified_name_without_app(self) -> None:
        tool = MCPTool(name="extract", description="Extract data")
        assert tool.qualified_name == "extract"

    def test_to_openai_schema(self) -> None:
        tool = MCPTool(
            name="validate",
            description="Validate policy",
            input_schema={"type": "object", "properties": {"amount": {"type": "number"}}},
            app_name="policy",
        )
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "policy__validate"
        assert schema["function"]["description"] == "Validate policy"
        assert "properties" in schema["function"]["parameters"]


class TestMCPToolResult:
    def test_success_result(self) -> None:
        result = MCPToolResult(
            tool_name="test",
            content="Success",
            is_error=False,
        )
        assert not result.is_error
        assert result.content == "Success"

    def test_error_result(self) -> None:
        result = MCPToolResult(
            tool_name="test",
            content="Something failed",
            is_error=True,
        )
        assert result.is_error

    def test_result_with_artifacts(self) -> None:
        result = MCPToolResult(
            tool_name="test",
            content="Done",
            artifacts=[
                MCPArtifact(content_type="text/html", content="<h1>Hi</h1>", name="report.html")
            ],
        )
        assert result.artifacts is not None
        assert len(result.artifacts) == 1
        assert result.artifacts[0].content_type == "text/html"


class TestMCPApp:
    def test_create(self) -> None:
        app = MCPApp(
            name="test",
            description="Test app",
            transport="stdio",
            command=["python", "-m", "test"],
        )
        assert app.name == "test"
        assert not app.connected
        assert app.tools == []
