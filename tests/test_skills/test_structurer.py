"""Tests for the skill auto-structurer."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from proceda.config import LLMConfig
from proceda.skills.structurer import auto_structure

WELL_FORMATTED = """\
---
name: test-skill
description: A well-formatted skill
---

### Step 1: First step
Do the first thing.

### Step 2: Second step
Do the second thing.
"""

UNSTRUCTURED = """\
---
name: plan-week
description: Weekly planning workflow
---

# 1. Review calendar
Check your calendar for the week.

# 2. Set priorities
Decide on top 3 priorities.

# 3. Block time
Block time for deep work.
"""

LLM_RESTRUCTURED_BODY = """\
### Step 1: Review calendar
Check your calendar for the week.

### Step 2: Set priorities
Decide on top 3 priorities.

### Step 3: Block time
Block time for deep work.
"""


class TestAutoStructure:
    @pytest.mark.asyncio
    async def test_well_formatted_passes_through(self) -> None:
        """Well-formatted content is returned unchanged, no LLM call."""
        config = LLMConfig()
        with patch("proceda.skills.structurer.LLMRuntime") as mock_cls:
            result = await auto_structure(WELL_FORMATTED, config)
            mock_cls.assert_not_called()
        assert result == WELL_FORMATTED

    @pytest.mark.asyncio
    async def test_unstructured_triggers_llm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Content without valid steps triggers LLM restructuring."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig()

        mock_runtime = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = LLM_RESTRUCTURED_BODY
        mock_response.tool_calls = []
        mock_runtime.complete.return_value = mock_response

        with patch("proceda.skills.structurer.LLMRuntime", return_value=mock_runtime):
            result = await auto_structure(UNSTRUCTURED, config)

        mock_runtime.complete.assert_called_once()
        # Verify the result parses successfully
        from proceda.skills.parser import parse_skill

        skill = parse_skill(result)
        assert skill.name == "plan-week"
        assert len(skill.steps) == 3

    @pytest.mark.asyncio
    async def test_llm_failure_returns_original(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If LLM call fails, original content is returned."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig()

        mock_runtime = AsyncMock()
        mock_runtime.complete.side_effect = Exception("API error")

        with patch("proceda.skills.structurer.LLMRuntime", return_value=mock_runtime):
            result = await auto_structure(UNSTRUCTURED, config)

        assert result == UNSTRUCTURED

    @pytest.mark.asyncio
    async def test_no_api_key_returns_original(self) -> None:
        """If no API key is available, original content is returned."""
        config = LLMConfig(api_key_env="NONEXISTENT_KEY_12345")
        result = await auto_structure(UNSTRUCTURED, config)
        assert result == UNSTRUCTURED

    @pytest.mark.asyncio
    async def test_no_frontmatter_returns_original(self) -> None:
        """Content without frontmatter can't be restructured, returned as-is."""
        content = "# Just some markdown\nNo frontmatter here."
        config = LLMConfig()
        result = await auto_structure(content, config)
        assert result == content
