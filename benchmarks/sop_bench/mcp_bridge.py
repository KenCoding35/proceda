# ABOUTME: MCP stdio server that wraps SOP-Bench tool managers.
# ABOUTME: Converts Bedrock-format toolspecs to MCP format and dispatches tool calls.

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def convert_bedrock_toolspecs(bedrock_specs: list[dict]) -> list[dict]:
    """Convert Bedrock-format toolspecs to MCP tool format.

    Bedrock: [{"toolSpec": {"name": ..., "inputSchema": {"json": {schema}}}}]
    MCP:     [{"name": ..., "description": ..., "inputSchema": {schema}}]
    """
    mcp_tools = []
    for spec in bedrock_specs:
        tool_spec = spec.get("toolSpec", spec)
        input_schema = tool_spec.get("inputSchema", {})
        # Bedrock nests the actual schema under "json"
        if "json" in input_schema:
            input_schema = input_schema["json"]
        mcp_tools.append(
            {
                "name": tool_spec["name"],
                "description": tool_spec.get("description", ""),
                "inputSchema": input_schema,
            }
        )
    return mcp_tools


def handle_request(
    request: dict,
    manager: Any,
    mcp_tools: list[dict],
) -> dict | None:
    """Handle a single JSON-RPC request and return the response."""
    method = request.get("method", "")
    req_id = request.get("id")

    # Notifications (no id) don't get responses
    if req_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "sop-bench-bridge", "version": "0.1.0"},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": mcp_tools},
        }

    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            result = manager.process_tool_call(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(e)},
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def load_domain(domain: str, data_dir: str) -> tuple[Any, list[dict]]:
    """Dynamically load a SOP-Bench domain's tool manager and toolspecs."""
    domain_path = Path(data_dir) / domain

    # Load toolspecs
    toolspecs_path = domain_path / "toolspecs.json"
    with open(toolspecs_path) as f:
        bedrock_specs = json.load(f)

    # Dynamically import tools.py and instantiate the Manager class
    tools_path = domain_path / "tools.py"
    spec = importlib.util.spec_from_file_location(f"sop_bench_tools_{domain}", tools_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find the Manager class (convention: *Manager)
    manager_cls = None
    for name in dir(module):
        if name.endswith("Manager") and name != "ToolManager":
            manager_cls = getattr(module, name)
            break
    if manager_cls is None:
        raise RuntimeError(f"No *Manager class found in {tools_path}")

    manager = manager_cls()
    return manager, bedrock_specs


def main() -> None:
    parser = argparse.ArgumentParser(description="SOP-Bench MCP tool bridge")
    parser.add_argument("--domain", required=True, help="Benchmark domain name")
    parser.add_argument("--data-dir", required=True, help="Path to SOP-Bench benchmarks/data/")
    args = parser.parse_args()

    manager, bedrock_specs = load_domain(args.domain, args.data_dir)
    mcp_tools = convert_bedrock_toolspecs(bedrock_specs)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request = json.loads(line)
        response = handle_request(request, manager, mcp_tools)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
