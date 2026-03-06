"""ABOUTME: Context management: token budgeting and message window management.
ABOUTME: Handles tokenization, message trimming, and step summarization."""

from __future__ import annotations

import logging
from typing import Protocol

from proceda.session import RunMessage

logger = logging.getLogger(__name__)

TRUNCATION_NOTICE = "[Earlier messages were trimmed to fit context window.]"


class Tokenizer(Protocol):
    """Counts tokens in text."""

    def encode(self, text: str) -> list[int]: ...


class CharBasedTokenizer:
    """Estimates tokens by dividing character count."""

    def __init__(self, chars_per_token: int = 4) -> None:
        self._chars_per_token = chars_per_token

    def encode(self, text: str) -> list[int]:
        count = max(1, len(text) // self._chars_per_token) if text else 0
        return [0] * count


def get_tokenizer_for_model(model: str) -> Tokenizer:
    """Return a tokenizer appropriate for the given model."""
    model_lower = model.lower()

    # Gemini models use ~3 chars per token
    if "gemini" in model_lower:
        return CharBasedTokenizer(chars_per_token=3)

    # OpenAI and Claude models: try tiktoken
    if any(k in model_lower for k in ("gpt", "openai", "claude", "anthropic")):
        try:
            import tiktoken

            return tiktoken.get_encoding("cl100k_base")
        except ImportError:
            return CharBasedTokenizer(chars_per_token=4)

    return CharBasedTokenizer(chars_per_token=4)


class ContextManager:
    """Manages conversation context within token budget limits."""

    def __init__(
        self,
        max_tokens: int = 100000,
        reserve_tokens: int = 4096,
        model: str = "",
    ) -> None:
        self._max_tokens = max_tokens
        self._reserve_tokens = reserve_tokens
        self._tokenizer = get_tokenizer_for_model(model) if model else CharBasedTokenizer()

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using the configured tokenizer."""
        return len(self._tokenizer.encode(text))

    def count_message_tokens(self, message: RunMessage) -> int:
        """Count tokens in a message including content and metadata."""
        total = self.count_tokens(message.content)
        if message.tool_call_id:
            total += self.count_tokens(message.tool_call_id)
        if message.app_name:
            total += self.count_tokens(message.app_name)
        return total

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate. Kept for backward compatibility."""
        return self.count_tokens(text)

    def trim_messages(self, messages: list[RunMessage]) -> list[RunMessage]:
        """Trim messages to fit within budget, preserving system, critical, and recent."""
        if not messages:
            return messages

        system_messages = [m for m in messages if m.role == "system"]
        non_system = [m for m in messages if m.role != "system"]

        total_tokens = sum(self.count_message_tokens(m) for m in messages)
        budget = self._max_tokens - self._reserve_tokens

        if total_tokens <= budget:
            return messages

        # Separate critical and non-critical non-system messages
        critical = [m for m in non_system if m.is_critical]
        non_critical = [m for m in non_system if not m.is_critical]

        # Reserve budget for system + critical first
        system_tokens = sum(self.count_message_tokens(m) for m in system_messages)
        critical_tokens = sum(self.count_message_tokens(m) for m in critical)
        remaining_budget = budget - system_tokens - critical_tokens

        # Fill remaining budget with recent non-critical messages (newest first)
        kept_non_critical: list[RunMessage] = []
        tokens_used = 0
        for msg in reversed(non_critical):
            msg_tokens = self.count_message_tokens(msg)
            if tokens_used + msg_tokens > remaining_budget:
                break
            kept_non_critical.append(msg)
            tokens_used += msg_tokens

        trimmed = len(non_critical) - len(kept_non_critical)

        # Rebuild in original order: system, truncation notice, then chronological
        result = list(system_messages)

        if trimmed > 0:
            result.append(RunMessage.create("system", TRUNCATION_NOTICE))

        # Merge critical and kept non-critical in original order
        kept_set = set(id(m) for m in critical) | set(id(m) for m in kept_non_critical)
        for msg in non_system:
            if id(msg) in kept_set:
                result.append(msg)

        return result

    def summarize_completed_step(
        self,
        messages: list[RunMessage],
        step_index: int,
        step_title: str,
    ) -> RunMessage:
        """Summarize a completed step's messages into a single message."""
        tool_names: list[str] = []
        for m in messages:
            if m.app_name and m.app_name not in tool_names:
                tool_names.append(m.app_name)

        if tool_names:
            tools_str = ", ".join(tool_names)
            text = f"Step {step_index} ({step_title}): Completed. Tools used: {tools_str}."
        else:
            text = f"Step {step_index} ({step_title}): Completed."

        return RunMessage.create("system", text)
