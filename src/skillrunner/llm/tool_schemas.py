"""Control tool schemas: runtime-native tools injected into every LLM call."""

from __future__ import annotations

from typing import Any

CONTROL_TOOLS = {"complete_step", "request_clarification"}


def get_control_tool_schemas() -> list[dict[str, Any]]:
    """Return the tool schemas for runtime control tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "complete_step",
                "description": (
                    "Signal that the current step is complete. Call this when you have "
                    "finished all actions required for the current step."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Brief summary of what was accomplished in this step.",
                        }
                    },
                    "required": ["summary"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "request_clarification",
                "description": (
                    "Ask the user for clarification when the instructions are ambiguous "
                    "or missing required information."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The clarification question to ask the user.",
                        },
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of suggested options.",
                        },
                    },
                    "required": ["question"],
                },
            },
        },
    ]


def is_control_tool(tool_name: str) -> bool:
    """Check if a tool name is a runtime control tool."""
    return tool_name in CONTROL_TOOLS
