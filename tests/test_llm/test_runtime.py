"""ABOUTME: Tests for LLM runtime: retries, Gemini sanitization, formatting, thinking tags.
ABOUTME: Covers Items 1-4 of the LLM runtime backport."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from proceda.config import LLMConfig
from proceda.exceptions import LLMRateLimitError, LLMTimeoutError
from proceda.llm.runtime import (
    LLMRuntime,
    _sanitize_schema_for_gemini,
    format_assistant_tool_calls,
    format_tool_result,
    parse_thinking_tags,
)
from proceda.session import ToolCall


def _make_litellm_response(content: str = "ok", tool_calls: list | None = None):
    """Build a fake LiteLLM response object."""
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message)
    response = SimpleNamespace(choices=[choice])
    response.model_dump = lambda: {"choices": [{"message": {"content": content}}]}
    return response


# ---------------------------------------------------------------------------
# Item 1: Retry with exponential backoff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_on_rate_limit():
    import litellm

    config = LLMConfig(max_retries=3)
    runtime = LLMRuntime(config)

    mock_acompletion = AsyncMock(
        side_effect=[
            litellm.RateLimitError("rate limited", "provider", "model", None),
            litellm.RateLimitError("rate limited", "provider", "model", None),
            _make_litellm_response("success"),
        ]
    )

    sleep_waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_waits.append(seconds)

    with (
        patch("litellm.acompletion", mock_acompletion),
        patch("asyncio.sleep", fake_sleep),
    ):
        result = await runtime.complete([{"role": "user", "content": "hi"}])

    assert result.content == "success"
    assert mock_acompletion.call_count == 3
    assert sleep_waits == [1, 2]  # 2**0, 2**1


@pytest.mark.asyncio
async def test_timeout_fails_immediately():
    import litellm

    config = LLMConfig(max_retries=3)
    runtime = LLMRuntime(config)

    mock_acompletion = AsyncMock(side_effect=litellm.Timeout("timed out", "provider", "model"))

    with patch("litellm.acompletion", mock_acompletion):
        with pytest.raises(LLMTimeoutError):
            await runtime.complete([{"role": "user", "content": "hi"}])

    assert mock_acompletion.call_count == 1


@pytest.mark.asyncio
async def test_api_error_retry():
    import litellm

    config = LLMConfig(max_retries=3)
    runtime = LLMRuntime(config)

    mock_acompletion = AsyncMock(
        side_effect=[
            litellm.APIError("server error", "provider", "model", None, 500),
            litellm.APIError("server error", "provider", "model", None, 500),
            _make_litellm_response("recovered"),
        ]
    )

    with (
        patch("litellm.acompletion", mock_acompletion),
        patch("asyncio.sleep", AsyncMock()),
    ):
        result = await runtime.complete([{"role": "user", "content": "hi"}])

    assert result.content == "recovered"
    assert mock_acompletion.call_count == 3


@pytest.mark.asyncio
async def test_retries_exhausted_raises_last_error():
    import litellm

    config = LLMConfig(max_retries=2)
    runtime = LLMRuntime(config)

    mock_acompletion = AsyncMock(
        side_effect=litellm.RateLimitError("rate limited", "provider", "model", None)
    )

    with (
        patch("litellm.acompletion", mock_acompletion),
        patch("asyncio.sleep", AsyncMock()),
    ):
        with pytest.raises(LLMRateLimitError):
            await runtime.complete([{"role": "user", "content": "hi"}])

    assert mock_acompletion.call_count == 3  # initial + 2 retries


# ---------------------------------------------------------------------------
# Item 2: Gemini schema sanitization
# ---------------------------------------------------------------------------


def test_sanitize_anyof():
    schema = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
    result = _sanitize_schema_for_gemini(schema)
    assert result == {"type": "string"}


def test_sanitize_oneof():
    schema = {"oneOf": [{"type": "number"}, {"type": "string"}]}
    result = _sanitize_schema_for_gemini(schema)
    assert result == {"type": "number"}


def test_sanitize_allof():
    schema = {
        "allOf": [
            {"type": "object", "properties": {"a": {"type": "string"}}},
            {"properties": {"b": {"type": "integer"}}},
        ]
    }
    result = _sanitize_schema_for_gemini(schema)
    assert result["properties"]["a"] == {"type": "string"}
    assert result["properties"]["b"] == {"type": "integer"}


def test_sanitize_array_without_items():
    schema = {"type": "array"}
    result = _sanitize_schema_for_gemini(schema)
    assert result["items"] == {"type": "string"}


def test_sanitize_nested():
    schema = {
        "type": "object",
        "properties": {
            "field1": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "field2": {
                "type": "array",
                "items": {"oneOf": [{"type": "integer"}, {"type": "string"}]},
            },
        },
    }
    result = _sanitize_schema_for_gemini(schema)
    assert result["properties"]["field1"] == {"type": "string"}
    assert result["properties"]["field2"]["items"] == {"type": "integer"}


# ---------------------------------------------------------------------------
# Item 3: Message formatting helpers
# ---------------------------------------------------------------------------


def test_format_tool_result():
    result = format_tool_result("tc_123", "some output")
    assert result == {
        "role": "tool",
        "tool_call_id": "tc_123",
        "content": "some output",
    }


def test_format_tool_result_error():
    result = format_tool_result("tc_123", "not found", is_error=True)
    assert result == {
        "role": "tool",
        "tool_call_id": "tc_123",
        "content": "Error: not found",
    }


def test_format_assistant_tool_calls():
    tcs = [ToolCall(id="tc_1", name="read_file", arguments={"path": "/tmp/x"})]
    result = format_assistant_tool_calls(tcs)
    assert result["role"] == "assistant"
    assert result["content"] == ""
    assert len(result["tool_calls"]) == 1
    tc = result["tool_calls"][0]
    assert tc["id"] == "tc_1"
    assert tc["type"] == "function"
    assert tc["function"]["name"] == "read_file"
    assert tc["function"]["arguments"] == '{"path": "/tmp/x"}'


def test_format_assistant_tool_calls_with_text():
    tcs = [ToolCall(id="tc_1", name="do_thing", arguments={})]
    result = format_assistant_tool_calls(tcs, text="Let me do that.")
    assert result["content"] == "Let me do that."


# ---------------------------------------------------------------------------
# Item 4: Multi-block thinking tag parsing
# ---------------------------------------------------------------------------


def test_parse_no_thinking_blocks():
    blocks, cleaned = parse_thinking_tags("Hello world")
    assert blocks == []
    assert cleaned == "Hello world"


def test_parse_single_thinking_block():
    text = "Before <thinking>reasoning here</thinking> after"
    blocks, cleaned = parse_thinking_tags(text)
    assert blocks == ["reasoning here"]
    assert cleaned == "Before  after"


def test_parse_multiple_thinking_blocks():
    text = "<thinking>first</thinking> middle <thinking>second</thinking> end"
    blocks, cleaned = parse_thinking_tags(text)
    assert blocks == ["first", "second"]
    assert cleaned == "middle  end"


def test_parse_multiline_thinking():
    text = "<thinking>\nline 1\nline 2\n</thinking> rest"
    blocks, cleaned = parse_thinking_tags(text)
    assert blocks == ["line 1\nline 2"]
    assert cleaned == "rest"
