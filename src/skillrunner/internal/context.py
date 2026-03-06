"""Context management: token budgeting and message window management."""

from __future__ import annotations

from skillrunner.session import RunMessage


class ContextManager:
    """Manages conversation context within token budget limits."""

    def __init__(self, max_tokens: int = 100000, reserve_tokens: int = 4096) -> None:
        self._max_tokens = max_tokens
        self._reserve_tokens = reserve_tokens

    def trim_messages(self, messages: list[RunMessage]) -> list[RunMessage]:
        """Trim messages to fit within budget, preserving system and recent messages."""
        if not messages:
            return messages

        # Always keep the system message (first one)
        system_messages = [m for m in messages if m.role == "system"]
        non_system = [m for m in messages if m.role != "system"]

        # Estimate total tokens
        total_chars = sum(len(m.content) for m in messages)
        estimated_tokens = total_chars // 4  # rough estimate

        budget = self._max_tokens - self._reserve_tokens
        if estimated_tokens <= budget:
            return messages

        # Keep system messages + most recent non-system messages
        result = list(system_messages)
        chars_used = sum(len(m.content) for m in system_messages)
        budget_chars = budget * 4

        # Add messages from the end until budget is used
        kept: list[RunMessage] = []
        for msg in reversed(non_system):
            msg_chars = len(msg.content)
            if chars_used + msg_chars > budget_chars:
                break
            kept.append(msg)
            chars_used += msg_chars

        result.extend(reversed(kept))
        return result

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars per token)."""
        return len(text) // 4
