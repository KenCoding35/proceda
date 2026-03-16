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


class TestHeavyLoadTrimming:
    def test_100_messages_trimmed_to_budget(self) -> None:
        # CharBasedTokenizer: 4 chars = 1 token. 100 chars = 25 tokens per message.
        # System: 20 chars = 5 tokens. 100 messages * 25 = 2500 tokens.
        # Budget = 200 - 0 = 200 tokens. Should keep system + some recent messages.
        cm = ContextManager(max_tokens=200, reserve_tokens=0)
        messages = [RunMessage.create("system", "S" * 20)]
        for i in range(100):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(RunMessage.create(role, f"msg{i:03d}" + "x" * 96))
        result = cm.trim_messages(messages)
        assert result[0].role == "system"
        # Trimming happened
        assert len(result) < len(messages)
        # Most recent message is preserved
        assert result[-1].content == messages[-1].content
        # Truncation notice present
        assert any(m.content == TRUNCATION_NOTICE for m in result)

    def test_budget_boundary_exact(self) -> None:
        # Create messages whose total tokens exactly equal the budget.
        # CharBasedTokenizer: "abcd" = 1 token, "abcdabcd" = 2 tokens.
        cm = ContextManager(max_tokens=10, reserve_tokens=0)
        # 3 messages: system 4 tokens + user 3 tokens + assistant 3 tokens = 10
        messages = [
            RunMessage.create("system", "a" * 16),  # 4 tokens
            RunMessage.create("user", "b" * 12),  # 3 tokens
            RunMessage.create("assistant", "c" * 12),  # 3 tokens
        ]
        result = cm.trim_messages(messages)
        assert len(result) == 3
        assert not any(m.content == TRUNCATION_NOTICE for m in result)

    def test_budget_boundary_one_over(self) -> None:
        # One token over budget should trigger trimming of oldest non-critical.
        cm = ContextManager(max_tokens=10, reserve_tokens=0)
        # system 4 + user 4 + assistant 3 = 11, one over budget of 10
        messages = [
            RunMessage.create("system", "a" * 16),  # 4 tokens
            RunMessage.create("user", "b" * 16),  # 4 tokens
            RunMessage.create("assistant", "c" * 12),  # 3 tokens
        ]
        result = cm.trim_messages(messages)
        # User message (oldest non-critical) should be dropped
        assert not any(m.content == "b" * 16 for m in result)
        # Assistant message (most recent) should be kept
        assert result[-1].content == "c" * 12
        assert result[0].role == "system"
        assert any(m.content == TRUNCATION_NOTICE for m in result)


class TestMultipleCriticalMessages:
    def test_all_critical_preserved_under_pressure(self) -> None:
        # 10 critical messages among 50 non-critical, with a tight budget.
        # Each message ~25 tokens (100 chars). System = 5 tokens (20 chars).
        # Critical: 10 * 25 = 250 tokens. System: 5 tokens.
        # Budget: 300 tokens. Remaining for non-critical: 300 - 5 - 250 = 45 tokens (1 message).
        cm = ContextManager(max_tokens=300, reserve_tokens=0)
        messages = [RunMessage.create("system", "S" * 20)]
        critical_contents = []
        for i in range(60):
            is_crit = i % 6 == 0  # 10 critical messages at indices 0,6,12,...,54
            role = "user" if i % 2 == 0 else "assistant"
            content = f"{'CRIT' if is_crit else 'norm'}{i:03d}" + "x" * 93
            msg = RunMessage.create(role, content, is_critical=is_crit)
            messages.append(msg)
            if is_crit:
                critical_contents.append(content)

        result = cm.trim_messages(messages)
        result_contents = [m.content for m in result]
        for cc in critical_contents:
            assert cc in result_contents, f"Critical message missing: {cc[:20]}..."

    def test_critical_ordering_preserved(self) -> None:
        # After trimming, critical messages maintain original relative order.
        cm = ContextManager(max_tokens=100, reserve_tokens=0)
        messages = [RunMessage.create("system", "S" * 8)]
        critical_order = []
        for i in range(20):
            is_crit = i in (3, 7, 12, 18)
            role = "user" if i % 2 == 0 else "assistant"
            content = f"msg_{i:02d}" + "p" * 30
            messages.append(RunMessage.create(role, content, is_critical=is_crit))
            if is_crit:
                critical_order.append(content)

        result = cm.trim_messages(messages)
        result_critical = [m.content for m in result if m.is_critical]
        # All critical present
        assert result_critical == critical_order


class TestToolMessageTrimming:
    def test_tool_messages_with_metadata_counted(self) -> None:
        cm = ContextManager(max_tokens=100000, reserve_tokens=0)
        # Tool message with metadata should count more tokens than content alone
        tool_msg = RunMessage.create(
            "tool", "result", tool_call_id="tc_abcdef123456", app_name="filesystem__read"
        )
        plain_msg = RunMessage.create("assistant", "result")
        assert cm.count_message_tokens(tool_msg) > cm.count_message_tokens(plain_msg)

    def test_tool_messages_trimmed_when_old(self) -> None:
        # Old tool messages get trimmed like regular non-critical messages.
        cm = ContextManager(max_tokens=30, reserve_tokens=0)
        messages = [
            RunMessage.create("system", "S" * 8),  # 2 tokens
            RunMessage.create("tool", "old_tool_result" * 10, tool_call_id="tc_old", app_name="a"),
            RunMessage.create("user", "recent" * 4),  # 6 tokens ~24 chars
        ]
        result = cm.trim_messages(messages)
        # Old tool message should be trimmed
        assert not any(m.content == "old_tool_result" * 10 for m in result)
        # Recent message kept
        assert result[-1].content == "recent" * 4


class TestExtremeBudgets:
    def test_tiny_budget_keeps_system_only(self) -> None:
        # Budget so small that only the system message fits.
        # System: 2 tokens (8 chars). Budget: 3 tokens. No room for others.
        cm = ContextManager(max_tokens=3, reserve_tokens=0)
        messages = [
            RunMessage.create("system", "S" * 8),  # 2 tokens
            RunMessage.create("user", "U" * 100),  # 25 tokens
            RunMessage.create("assistant", "A" * 100),  # 25 tokens
        ]
        result = cm.trim_messages(messages)
        assert result[0].role == "system"
        assert result[0].content == "S" * 8
        # All non-system trimmed; truncation notice added
        assert any(m.content == TRUNCATION_NOTICE for m in result)

    def test_zero_reserve_tokens(self) -> None:
        # With reserve_tokens=0, full max_tokens budget is available.
        # System 2 + user 2 + assistant 2 = 6 tokens. Budget = 6.
        cm = ContextManager(max_tokens=6, reserve_tokens=0)
        messages = [
            RunMessage.create("system", "a" * 8),  # 2 tokens
            RunMessage.create("user", "b" * 8),  # 2 tokens
            RunMessage.create("assistant", "c" * 8),  # 2 tokens
        ]
        result = cm.trim_messages(messages)
        assert len(result) == 3

    def test_all_messages_critical(self) -> None:
        # When every non-system message is critical, they all survive trimming.
        # But remaining_budget for non-critical becomes negative, so no non-critical kept.
        cm = ContextManager(max_tokens=50, reserve_tokens=0)
        messages = [RunMessage.create("system", "S" * 8)]  # 2 tokens
        for i in range(5):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(RunMessage.create(role, f"crit{i}" + "x" * 20, is_critical=True))
        result = cm.trim_messages(messages)
        # All critical messages preserved
        critical_in = [m for m in messages if m.is_critical]
        critical_out = [m for m in result if m.is_critical]
        assert len(critical_out) == len(critical_in)
