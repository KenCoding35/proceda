"""ABOUTME: Tests for the MCP orchestrator.
ABOUTME: Covers tool discovery, access policies, denylist pattern matching, and required tools."""

from __future__ import annotations

from proceda.config import SecurityConfig
from proceda.mcp.models import MCPTool
from proceda.mcp.orchestrator import MCPOrchestrator


class TestMCPOrchestrator:
    def _create_orchestrator(
        self,
        tools: list[MCPTool] | None = None,
        denylist: list[str] | None = None,
        required_tools: list[str] | None = None,
    ) -> MCPOrchestrator:
        security = SecurityConfig(tool_denylist=denylist or [])
        orch = MCPOrchestrator(security=security, required_tools=required_tools)
        # Manually populate tools for testing
        if tools:
            for tool in tools:
                orch._tools[tool.qualified_name] = tool
        return orch

    def test_tool_allowed_no_restrictions(self) -> None:
        orch = self._create_orchestrator(
            tools=[MCPTool(name="tool_a", description="A", app_name="app")]
        )
        assert orch._is_tool_allowed("app__tool_a")

    def test_tool_denied_by_denylist(self) -> None:
        orch = self._create_orchestrator(
            tools=[MCPTool(name="destroy", description="D", app_name="dangerous")],
            denylist=["dangerous__*"],
        )
        assert not orch._is_tool_allowed("dangerous__destroy")

    def test_tool_allowed_not_in_denylist(self) -> None:
        orch = self._create_orchestrator(
            tools=[MCPTool(name="safe", description="S", app_name="app")],
            denylist=["dangerous__*"],
        )
        assert orch._is_tool_allowed("app__safe")

    def test_tool_denied_by_required_tools(self) -> None:
        orch = self._create_orchestrator(
            tools=[
                MCPTool(name="tool_a", description="A", app_name="app"),
                MCPTool(name="tool_b", description="B", app_name="app"),
            ],
            required_tools=["app__tool_a"],
        )
        assert orch._is_tool_allowed("app__tool_a")
        assert not orch._is_tool_allowed("app__tool_b")

    def test_get_tool_schemas(self) -> None:
        orch = self._create_orchestrator(
            tools=[
                MCPTool(name="extract", description="Extract", app_name="receipts"),
                MCPTool(name="validate", description="Validate", app_name="policy"),
            ]
        )
        schemas = orch.get_tool_schemas()
        assert len(schemas) == 2
        names = {s["function"]["name"] for s in schemas}
        assert names == {"receipts__extract", "policy__validate"}

    def test_get_available_tools(self) -> None:
        orch = self._create_orchestrator(
            tools=[
                MCPTool(name="safe", description="S", app_name="app"),
                MCPTool(name="blocked", description="B", app_name="dangerous"),
            ],
            denylist=["dangerous__*"],
        )
        available = orch.get_available_tools()
        assert len(available) == 1
        assert available[0].qualified_name == "app__safe"

    def test_check_required_tools_all_present(self) -> None:
        orch = self._create_orchestrator(
            tools=[
                MCPTool(name="tool_a", description="A", app_name="app"),
                MCPTool(name="tool_b", description="B", app_name="app"),
            ],
            required_tools=["app__tool_a", "app__tool_b"],
        )
        missing = orch.check_required_tools()
        assert missing == []

    def test_check_required_tools_some_missing(self) -> None:
        orch = self._create_orchestrator(
            tools=[MCPTool(name="tool_a", description="A", app_name="app")],
            required_tools=["app__tool_a", "app__tool_b"],
        )
        missing = orch.check_required_tools()
        assert "app__tool_b" in missing

    def test_resolve_tool_qualified(self) -> None:
        tool = MCPTool(name="extract", description="E", app_name="receipts")
        orch = self._create_orchestrator(tools=[tool])
        found = orch.resolve_tool("receipts__extract")
        assert found is not None
        assert found.name == "extract"

    def test_resolve_tool_unqualified(self) -> None:
        tool = MCPTool(name="extract", description="E", app_name="receipts")
        orch = self._create_orchestrator(tools=[tool])
        found = orch.resolve_tool("extract")
        assert found is not None

    def test_resolve_tool_not_found(self) -> None:
        orch = self._create_orchestrator()
        assert orch.resolve_tool("nonexistent") is None


class TestDenylistPatterns:
    """Tests for fnmatch-based tool denylist enforcement."""

    def _make_orchestrator(
        self, tool_names: list[tuple[str, str]], denylist: list[str]
    ) -> MCPOrchestrator:
        security = SecurityConfig(tool_denylist=denylist)
        orch = MCPOrchestrator(security=security)
        for app_name, tool_name in tool_names:
            tool = MCPTool(name=tool_name, description="", app_name=app_name)
            orch._tools[tool.qualified_name] = tool
        return orch

    def test_wildcard_match(self) -> None:
        orch = self._make_orchestrator(
            [("bad", "tool1"), ("bad", "tool2"), ("good", "tool1")],
            denylist=["bad__*"],
        )
        assert not orch._is_tool_allowed("bad__tool1")
        assert not orch._is_tool_allowed("bad__tool2")
        assert orch._is_tool_allowed("good__tool1")

    def test_exact_match(self) -> None:
        orch = self._make_orchestrator(
            [("app", "delete"), ("app", "read")],
            denylist=["app__delete"],
        )
        assert not orch._is_tool_allowed("app__delete")
        assert orch._is_tool_allowed("app__read")

    def test_multiple_patterns(self) -> None:
        orch = self._make_orchestrator(
            [("danger", "nuke"), ("evil", "hack"), ("safe", "read")],
            denylist=["danger__*", "evil__*"],
        )
        assert not orch._is_tool_allowed("danger__nuke")
        assert not orch._is_tool_allowed("evil__hack")
        assert orch._is_tool_allowed("safe__read")

    def test_no_match(self) -> None:
        orch = self._make_orchestrator(
            [("app", "read")],
            denylist=["other__*"],
        )
        assert orch._is_tool_allowed("app__read")

    def test_empty_denylist(self) -> None:
        orch = self._make_orchestrator(
            [("app", "anything")],
            denylist=[],
        )
        assert orch._is_tool_allowed("app__anything")

    def test_all_tools_denied(self) -> None:
        orch = self._make_orchestrator(
            [("app", "read"), ("app", "write")],
            denylist=["*"],
        )
        assert not orch._is_tool_allowed("app__read")
        assert not orch._is_tool_allowed("app__write")
        assert orch.get_available_tools() == []

    def test_case_sensitivity(self) -> None:
        """fnmatch is case-sensitive on POSIX; tool names should match exactly."""
        orch = self._make_orchestrator(
            [("App", "Read")],
            denylist=["app__read"],
        )
        # "App__Read" should NOT match "app__read" (case-sensitive)
        assert orch._is_tool_allowed("App__Read")
