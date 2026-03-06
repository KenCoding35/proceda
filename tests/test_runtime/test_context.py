"""Tests for context management."""

from __future__ import annotations

from proceda.internal.context import ContextManager
from proceda.session import RunMessage


class TestContextManager:
    def test_no_trimming_under_budget(self) -> None:
        cm = ContextManager(max_tokens=100000)
        messages = [
            RunMessage.create("system", "System prompt"),
            RunMessage.create("user", "Hello"),
            RunMessage.create("assistant", "Hi there"),
        ]
        result = cm.trim_messages(messages)
        assert len(result) == 3

    def test_trimming_preserves_system(self) -> None:
        cm = ContextManager(max_tokens=100, reserve_tokens=10)
        messages = [
            RunMessage.create("system", "S" * 50),
            RunMessage.create("user", "U" * 200),
            RunMessage.create("assistant", "A" * 200),
            RunMessage.create("user", "Recent" * 5),
        ]
        result = cm.trim_messages(messages)
        # System message should always be first
        assert result[0].role == "system"

    def test_empty_messages(self) -> None:
        cm = ContextManager()
        assert cm.trim_messages([]) == []

    def test_estimate_tokens(self) -> None:
        cm = ContextManager()
        assert cm.estimate_tokens("hello world") == 2  # 11 chars / 4


class TestContextManagerEdgeCases:
    def test_single_system_message(self) -> None:
        cm = ContextManager(max_tokens=100)
        messages = [RunMessage.create("system", "Short")]
        result = cm.trim_messages(messages)
        assert len(result) == 1

    def test_recent_messages_preferred(self) -> None:
        cm = ContextManager(max_tokens=200, reserve_tokens=10)
        messages = [
            RunMessage.create("system", "S" * 10),
            RunMessage.create("user", "Old" * 100),
            RunMessage.create("assistant", "Old response" * 100),
            RunMessage.create("user", "New" * 10),
        ]
        result = cm.trim_messages(messages)
        # Most recent messages should be kept
        assert result[-1].content == "New" * 10
