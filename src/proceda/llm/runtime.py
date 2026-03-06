"""LLM runtime: wraps LiteLLM for model calls with tool support."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from proceda.config import LLMConfig
from proceda.exceptions import LLMError
from proceda.session import RunMessage, ToolCall

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Parsed response from an LLM call."""

    content: str | None
    tool_calls: list[ToolCall]
    reasoning: str | None = None
    raw_response: dict[str, Any] | None = None


class LLMRuntime:
    """Wraps LiteLLM for making LLM API calls."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._model = config.model

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Make an LLM completion call."""
        try:
            import litellm

            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": self._config.temperature,
                "max_tokens": self._config.max_tokens,
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await litellm.acompletion(**kwargs)
            return self._parse_response(response)

        except ImportError:
            raise LLMError(
                "litellm is required but not installed. Install with: pip install litellm"
            )
        except Exception as e:
            raise LLMError(f"LLM call failed: {e}") from e

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse a LiteLLM response into our internal model."""
        choice = response.choices[0]
        message = choice.message

        content = message.content
        reasoning = None
        tool_calls: list[ToolCall] = []

        # Extract reasoning if present (e.g., from <thinking> tags)
        if content and "<thinking>" in content:
            import re

            thinking_match = re.search(r"<thinking>(.*?)</thinking>", content, re.DOTALL)
            if thinking_match:
                reasoning = thinking_match.group(1).strip()
                content = re.sub(r"<thinking>.*?</thinking>", "", content, flags=re.DOTALL).strip()

        # Parse tool calls
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                import json

                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {"raw": tc.function.arguments}

                tool_calls.append(
                    ToolCall(
                        id=tc.id or ToolCall.generate_id(),
                        name=tc.function.name,
                        arguments=args,
                    )
                )

        return LLMResponse(
            content=content if content else None,
            tool_calls=tool_calls,
            reasoning=reasoning,
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )

    def format_messages(self, run_messages: list[RunMessage]) -> list[dict[str, Any]]:
        """Convert internal RunMessages to LiteLLM message format."""
        formatted: list[dict[str, Any]] = []

        for msg in run_messages:
            entry: dict[str, Any] = {
                "role": msg.role,
                "content": msg.content,
            }

            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id

            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": __import__("json").dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]

            formatted.append(entry)

        return formatted
