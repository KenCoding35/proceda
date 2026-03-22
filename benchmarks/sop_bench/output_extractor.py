# ABOUTME: Extracts structured output fields from Proceda run events.
# ABOUTME: Tries tool results, then XML tags, then JSON blocks from assistant messages.

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

    Tries multiple strategies in order:
    1. TOOL_COMPLETED events (deterministic, from tool calls)
    2. XML tags matching expected column names from assistant messages
    3. <final_output>{JSON}</final_output> from assistant messages
    4. Bare JSON blocks from assistant messages

    Returns the first strategy that finds all expected columns, or the
    best partial result.
    """
    output = _extract_from_tool_results(events, expected_columns)
    if _has_all_columns(output, expected_columns):
        return output

    # Try assistant message strategies, merge with any tool results found
    msg_output = _extract_from_assistant_messages(events, expected_columns)
    # Tool results take priority, fill gaps with message extraction
    merged = {**msg_output, **output}
    return {k: v for k, v in merged.items() if k in set(expected_columns)}


def _has_all_columns(output: dict, expected_columns: list[str]) -> bool:
    return all(col in output for col in expected_columns)


def _extract_from_tool_results(
    events: list[RunEvent],
    expected_columns: list[str],
) -> dict[str, Any]:
    """Extract output fields from TOOL_COMPLETED event payloads."""
    expected_set = set(expected_columns)
    output: dict[str, Any] = {}

    tool_completed_events = [e for e in events if e.type == EventType.TOOL_COMPLETED]

    for event in tool_completed_events:
        result_text = event.payload.get("result", "")
        try:
            result_parsed = json.loads(result_text)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(result_parsed, dict):
            for key, value in result_parsed.items():
                if key in expected_set:
                    output[key] = value
        elif isinstance(result_parsed, str | int | float) and len(expected_columns) == 1:
            # Single expected column + bare value from last tool → assign it
            output[expected_columns[0]] = result_parsed

    return output


def _extract_from_assistant_messages(
    events: list[RunEvent],
    expected_columns: list[str],
) -> dict[str, Any]:
    """Extract from assistant messages using multiple strategies."""
    expected_set = set(expected_columns)

    # Collect all text content from assistant messages and step summaries
    all_content = []
    for event in events:
        if event.type == EventType.MESSAGE_ASSISTANT:
            content = event.payload.get("content", "")
            if content:
                all_content.append(content)
        elif event.type == EventType.SUMMARY_GENERATED:
            summary = event.payload.get("summary", "")
            if summary:
                all_content.append(summary)

    if not all_content:
        return {}

    # Try each strategy across all messages (last message first)
    for content in reversed(all_content):
        # Strategy 1: XML tags matching column names (e.g., <hazard_class>...</hazard_class>)
        result = _extract_xml_tags(content, expected_set)
        if result:
            return result

        # Strategy 2: <final_output>{JSON}</final_output>
        result = _extract_final_output_json(content, expected_set)
        if result:
            return result

        # Strategy 3: Bare JSON object in content
        result = _extract_bare_json(content, expected_set)
        if result:
            return result

        # Strategy 4: Prose patterns (e.g., "final_resolution_status is RESOLVED")
        result = _extract_prose_values(content, expected_set)
        if result:
            return result

    return {}


def _extract_xml_tags(content: str, expected_set: set[str]) -> dict[str, Any]:
    """Extract values from XML tags matching expected column names."""
    output: dict[str, Any] = {}
    for col in expected_set:
        pattern = rf"<{col}>(.*?)</{col}>"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            output[col] = match.group(1).strip()
    return output


def _extract_prose_values(content: str, expected_set: set[str]) -> dict[str, Any]:
    """Extract values mentioned in prose near expected column names.

    Matches patterns like:
    - "final_resolution_status: PENDING_ACTION"
    - "the final_resolution_status is RESOLVED"
    - "status is PENDING_ACTION"
    - "hazard_class: Hazard Class A"
    """
    output: dict[str, Any] = {}
    for col in expected_set:
        # Convert column name to flexible pattern (underscores → spaces or underscores)
        col_pattern = col.replace("_", r"[\s_]")
        # Also try matching the last segment of the column name (e.g., "status" from
        # "final_resolution_status") to handle aliases like "ticket status"
        col_parts = col.split("_")
        alt_patterns = [col_pattern]
        if len(col_parts) > 1:
            alt_patterns.append(r"[\w\s]*" + col_parts[-1])
        for cp in alt_patterns:
            # Match: column_name followed by separator then value
            pattern = (
                rf"(?:{cp})\s*(?:is|:|=|as)\s*[\"']?"
                rf"([\w\s\-]+?)[\"']?"
                rf"(?:\.|,|\s*$|\s+(?:and|for|with|due|await|based))"
            )
            # Use findall and take the LAST match (final status is typically at the end)
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                output[col] = matches[-1].group(1).strip()
                break
    return output


def _extract_final_output_json(content: str, expected_set: set[str]) -> dict[str, Any]:
    """Extract from <final_output>{JSON}</final_output>."""
    match = re.search(r"<final_output>(.*?)</final_output>", content, re.DOTALL)
    if not match:
        return {}
    try:
        result_dict = json.loads(match.group(1))
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(result_dict, dict):
        return {}
    return {k: v for k, v in result_dict.items() if k in expected_set}


def _extract_bare_json(content: str, expected_set: set[str]) -> dict[str, Any]:
    """Extract from bare JSON objects in the content."""
    for match in re.finditer(r"\{[^{}]+\}", content):
        try:
            result_dict = json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(result_dict, dict):
            continue
        extracted = {k: v for k, v in result_dict.items() if k in expected_set}
        if extracted:
            return extracted
    return {}
