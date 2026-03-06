# ABOUTME: Tests for context management: trimming, tokenization, critical preservation,
# ABOUTME: and step summarization.

from __future__ import annotations

from proceda.internal.context import (
    TRUNCATION_NOTICE,
    CharBasedTokenizer,
    ContextManager,
    get_tokenizer_for_model,
)
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


class TestTokenizer:
    def test_char_based_tokenizer(self) -> None:
        tok = CharBasedTokenizer(chars_per_token=4)
        tokens = tok.encode("hello world!!")  # 13 chars -> 3 tokens
        assert len(tokens) == 3

    def test_get_tokenizer_openai(self) -> None:
        tok = get_tokenizer_for_model("gpt-4")
        # Should be tiktoken-based (not CharBasedTokenizer)
        assert not isinstance(tok, CharBasedTokenizer)
        # Should produce reasonable token counts
        assert len(tok.encode("hello world")) > 0

    def test_get_tokenizer_claude(self) -> None:
        tok = get_tokenizer_for_model("anthropic/claude-3")
        assert not isinstance(tok, CharBasedTokenizer)
        assert len(tok.encode("hello world")) > 0

    def test_get_tokenizer_gemini(self) -> None:
        tok = get_tokenizer_for_model("gemini/pro")
        assert isinstance(tok, CharBasedTokenizer)
        # Gemini uses 3 chars per token
        assert len(tok.encode("123456789")) == 3

    def test_get_tokenizer_unknown(self) -> None:
        tok = get_tokenizer_for_model("unknown")
        assert isinstance(tok, CharBasedTokenizer)
        # Default uses 4 chars per token
        assert len(tok.encode("12345678")) == 2

    def test_count_tokens(self) -> None:
        cm = ContextManager(model="gpt-4")
        count = cm.count_tokens("hello world")
        assert count > 0

    def test_count_message_tokens(self) -> None:
        cm = ContextManager(model="gpt-4")
        msg = RunMessage.create("tool", "result data", tool_call_id="tc_abc123", app_name="myapp")
        tokens = cm.count_message_tokens(msg)
        content_tokens = cm.count_tokens("result data")
        # Should be more than just content since it includes metadata
        assert tokens > content_tokens


class TestStepSummarization:
    def test_summarize_with_tools(self) -> None:
        cm = ContextManager()
        messages = [
            RunMessage.create("user", "Do the step"),
            RunMessage.create("assistant", "I'll use tools"),
            RunMessage.create("tool", "file content", app_name="filesystem__read"),
            RunMessage.create("tool", "search results", app_name="search__query"),
        ]
        summary = cm.summarize_completed_step(messages, 1, "Gather info")
        assert "Step 1 (Gather info): Completed." in summary.content
        assert "filesystem__read" in summary.content
        assert "search__query" in summary.content

    def test_summarize_without_tools(self) -> None:
        cm = ContextManager()
        messages = [
            RunMessage.create("user", "Do the step"),
            RunMessage.create("assistant", "Done thinking"),
        ]
        summary = cm.summarize_completed_step(messages, 2, "Think")
        assert summary.content == "Step 2 (Think): Completed."

    def test_summary_deduplicates_tools(self) -> None:
        cm = ContextManager()
        messages = [
            RunMessage.create("tool", "result 1", app_name="filesystem__read"),
            RunMessage.create("tool", "result 2", app_name="filesystem__read"),
            RunMessage.create("tool", "result 3", app_name="filesystem__read"),
        ]
        summary = cm.summarize_completed_step(messages, 1, "Read files")
        # Tool name should appear only once
        assert summary.content.count("filesystem__read") == 1


class TestCriticalMessagePreservation:
    def test_critical_messages_survive_trimming(self) -> None:
        cm = ContextManager(max_tokens=100, reserve_tokens=10)
        messages = [
            RunMessage.create("system", "S" * 20),
            RunMessage.create("user", "Old" * 50),
            RunMessage.create("user", "Critical step prompt", is_critical=True),
            RunMessage.create("assistant", "A" * 200),
            RunMessage.create("user", "Recent" * 5),
        ]
        result = cm.trim_messages(messages)
        critical_msgs = [m for m in result if m.is_critical]
        assert len(critical_msgs) == 1
        assert critical_msgs[0].content == "Critical step prompt"

    def test_non_critical_trimmed_first(self) -> None:
        cm = ContextManager(max_tokens=80, reserve_tokens=10)
        messages = [
            RunMessage.create("system", "S" * 20),
            RunMessage.create("user", "Old non-critical" * 20),
            RunMessage.create("tool", "Critical answer", is_critical=True),
            RunMessage.create("user", "Recent" * 5),
        ]
        result = cm.trim_messages(messages)
        # Critical message must be present
        assert any(m.content == "Critical answer" for m in result)
        # System message is always first
        assert result[0].role == "system"

    def test_truncation_notice_added(self) -> None:
        cm = ContextManager(max_tokens=80, reserve_tokens=10)
        messages = [
            RunMessage.create("system", "S" * 20),
            RunMessage.create("user", "Old" * 100),
            RunMessage.create("assistant", "Old resp" * 100),
            RunMessage.create("user", "Recent" * 5),
        ]
        result = cm.trim_messages(messages)
        # Should have a truncation notice
        notice_msgs = [m for m in result if m.content == TRUNCATION_NOTICE]
        assert len(notice_msgs) == 1

    def test_all_messages_kept_when_under_budget(self) -> None:
        cm = ContextManager(max_tokens=100000)
        messages = [
            RunMessage.create("system", "System prompt"),
            RunMessage.create("user", "Hello"),
            RunMessage.create("assistant", "Hi"),
        ]
        result = cm.trim_messages(messages)
        assert len(result) == 3
        # No truncation notice
        assert not any(m.content == TRUNCATION_NOTICE for m in result)
