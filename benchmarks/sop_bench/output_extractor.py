# ABOUTME: Extracts structured output fields from Proceda run events.
# ABOUTME: Primary source is TOOL_COMPLETED events; falls back to assistant message parsing.

from __future__ import annotations

import json
import re
from typing import Any

from proceda.events import EventType, RunEvent


def extract_output(
    events: list[RunEvent],
    expected_columns: list[str],
) -> dict[str, Any]:
    """Extract output fields from Proceda run events.

    Tries TOOL_COMPLETED events first (deterministic). If insufficient fields
    are found, falls back to parsing <final_output> JSON from the last
    assistant message.
    """
    output = _extract_from_tool_results(events, expected_columns)
    if output:
        return output
    return _extract_from_assistant_message(events, expected_columns)


def _extract_from_tool_results(
    events: list[RunEvent],
    expected_columns: list[str],
) -> dict[str, Any]:
    """Extract output fields from TOOL_COMPLETED event payloads."""
    expected_set = set(expected_columns)
    output: dict[str, Any] = {}

    for event in events:
        if event.type != EventType.TOOL_COMPLETED:
            continue
        result_text = event.payload.get("result", "")
        try:
            result_dict = json.loads(result_text)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(result_dict, dict):
            continue
        for key, value in result_dict.items():
            if key in expected_set:
                output[key] = value

    return output


def _extract_from_assistant_message(
    events: list[RunEvent],
    expected_columns: list[str],
) -> dict[str, Any]:
    """Fall back: parse <final_output>{JSON}</final_output> from the last assistant message."""
    expected_set = set(expected_columns)

    # Find the last assistant message
    for event in reversed(events):
        if event.type != EventType.MESSAGE_ASSISTANT:
            continue
        content = event.payload.get("content", "")
        match = re.search(r"<final_output>(.*?)</final_output>", content, re.DOTALL)
        if not match:
            continue
        try:
            result_dict = json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(result_dict, dict):
            continue
        return {k: v for k, v in result_dict.items() if k in expected_set}

    return {}
