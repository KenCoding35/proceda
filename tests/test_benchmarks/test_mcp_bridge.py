# ABOUTME: Tests for the SOP-Bench MCP tool bridge server.
# ABOUTME: Verifies toolspec conversion, tool dispatch, and JSON-RPC protocol handling.

from __future__ import annotations

import json

from benchmarks.sop_bench.mcp_bridge import convert_bedrock_toolspecs, handle_request

SAMPLE_BEDROCK_TOOLSPECS = [
    {
        "toolSpec": {
            "name": "validateInsurance",
            "description": "Validates insurance coverage",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string", "description": "Patient ID"},
                        "policy_number": {"type": "string", "description": "Policy number"},
                    },
                    "required": ["patient_id", "policy_number"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "verifyPharmacy",
            "description": "Verifies pharmacy details",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "pharmacy_name": {"type": "string"},
                    },
                    "required": ["pharmacy_name"],
                }
            },
        }
    },
]


class FakeToolManager:
    """Mimics SOP-Bench's *Manager.process_tool_call interface."""

    def process_tool_call(self, tool_name: str, tool_input: dict) -> dict:
        if tool_name == "validateInsurance":
            return {"insurance_validation": "valid"}
        if tool_name == "verifyPharmacy":
            return {"pharmacy_check": "yes"}
        raise ValueError(f"Unknown tool: {tool_name}")


class TestConvertBedrockToolspecs:
    def test_converts_single_tool(self):
        mcp_tools = convert_bedrock_toolspecs(SAMPLE_BEDROCK_TOOLSPECS[:1])
        assert len(mcp_tools) == 1
        tool = mcp_tools[0]
        assert tool["name"] == "validateInsurance"
        assert tool["description"] == "Validates insurance coverage"
        assert tool["inputSchema"]["type"] == "object"
        assert "patient_id" in tool["inputSchema"]["properties"]

    def test_converts_multiple_tools(self):
        mcp_tools = convert_bedrock_toolspecs(SAMPLE_BEDROCK_TOOLSPECS)
        assert len(mcp_tools) == 2
        names = [t["name"] for t in mcp_tools]
        assert names == ["validateInsurance", "verifyPharmacy"]

    def test_strips_bedrock_wrapper(self):
        """Bedrock nests under toolSpec.inputSchema.json; MCP uses inputSchema."""
        mcp_tools = convert_bedrock_toolspecs(SAMPLE_BEDROCK_TOOLSPECS)
        for tool in mcp_tools:
            assert "toolSpec" not in tool
            assert "json" not in tool.get("inputSchema", {})
            assert tool["inputSchema"]["type"] == "object"

    def test_empty_list(self):
        assert convert_bedrock_toolspecs([]) == []


class TestHandleRequest:
    def setup_method(self):
        self.manager = FakeToolManager()
        self.mcp_tools = convert_bedrock_toolspecs(SAMPLE_BEDROCK_TOOLSPECS)

    def test_initialize(self):
        resp = handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            self.manager,
            self.mcp_tools,
        )
        assert resp["id"] == 1
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert "tools" in resp["result"]["capabilities"]

    def test_tools_list(self):
        resp = handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            self.manager,
            self.mcp_tools,
        )
        tools = resp["result"]["tools"]
        assert len(tools) == 2
        assert tools[0]["name"] == "validateInsurance"

    def test_tools_call_success(self):
        resp = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "validateInsurance",
                    "arguments": {"patient_id": "P100012", "policy_number": "INS567890"},
                },
            },
            self.manager,
            self.mcp_tools,
        )
        assert "result" in resp
        content = resp["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        parsed = json.loads(content[0]["text"])
        assert parsed == {"insurance_validation": "valid"}

    def test_tools_call_unknown_tool(self):
        resp = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "nonexistent", "arguments": {}},
            },
            self.manager,
            self.mcp_tools,
        )
        assert "error" in resp

    def test_unknown_method(self):
        resp = handle_request(
            {"jsonrpc": "2.0", "id": 5, "method": "foo/bar", "params": {}},
            self.manager,
            self.mcp_tools,
        )
        assert "error" in resp

    def test_notifications_ignored(self):
        """JSON-RPC notifications (no id) like notifications/initialized should return None."""
        resp = handle_request(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            self.manager,
            self.mcp_tools,
        )
        assert resp is None
