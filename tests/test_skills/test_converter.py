"""Tests for the SOP converter."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from proceda.config import LLMConfig
from proceda.exceptions import ConversionError
from proceda.skills.converter import convert_sop

PLAIN_TEXT_SOP = """\
Employee Onboarding Process

1. Collect new hire paperwork
   - Tax forms (W-4, I-9)
   - Direct deposit information
   - Emergency contact

2. Set up accounts
   - Create email account
   - Provision laptop
   - Grant building access

3. Schedule orientation
   - Book conference room
   - Send calendar invite
   - Prepare welcome packet
"""

PROSE_SOP = """\
When a customer submits a refund request, first verify their purchase in the \
order management system. Check that the item is within the 30-day return window \
and that the reason qualifies under our policy.

If everything checks out, process the refund through the payment gateway. \
Make sure to get manager approval before issuing refunds over $500.

Finally, send the customer a confirmation email with the refund details and \
expected timeline.
"""

VALID_SKILL_OUTPUT = """\
---
name: employee-onboarding
description: Process for onboarding new employees
---

### Step 1: Collect new hire paperwork
Gather all required documents from the new hire:
- Tax forms (W-4, I-9)
- Direct deposit information
- Emergency contact

### Step 2: Set up accounts
Create and provision all necessary accounts:
- Create email account
- Provision laptop
- Grant building access

### Step 3: Schedule orientation
Prepare and schedule the orientation session:
- Book conference room
- Send calendar invite
- Prepare welcome packet
"""

VALID_SKILL_WITH_MARKERS = """\
---
name: customer-refund
description: Process customer refund requests with approval gates
---

### Step 1: Verify purchase
Verify the customer's purchase in the order management system. Check that the \
item is within the 30-day return window and that the reason qualifies under policy.

### Step 2: Process refund
[APPROVAL REQUIRED]
Process the refund through the payment gateway.

### Step 3: Send confirmation
Send the customer a confirmation email with refund details and expected timeline.
"""

MALFORMED_OUTPUT = """\
## Step 1: Do something
This uses wrong heading level.
"""

FENCED_OUTPUT = """\
```markdown
---
name: test-skill
description: A test skill
---

### Step 1: Do the thing
Do it well.
```
"""

VALID_SKILL_WITH_NAME_HINT = """\
---
name: custom-name
description: A custom named skill
---

### Step 1: Do something
Content here.
"""


class TestConvertSop:
    @pytest.mark.asyncio
    async def test_converts_plain_text_sop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Plain numbered list is converted to valid SKILL.md."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig()

        mock_runtime = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = VALID_SKILL_OUTPUT
        mock_response.tool_calls = []
        mock_runtime.complete.return_value = mock_response

        with patch("proceda.skills.converter.LLMRuntime", return_value=mock_runtime):
            result = await convert_sop(PLAIN_TEXT_SOP, config)

        from proceda.skills.parser import parse_skill

        skill = parse_skill(result)
        assert skill.name == "employee-onboarding"
        assert skill.step_count == 3

    @pytest.mark.asyncio
    async def test_converts_prose_sop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Narrative prose is converted to valid SKILL.md with markers."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig()

        mock_runtime = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = VALID_SKILL_WITH_MARKERS
        mock_response.tool_calls = []
        mock_runtime.complete.return_value = mock_response

        with patch("proceda.skills.converter.LLMRuntime", return_value=mock_runtime):
            result = await convert_sop(PROSE_SOP, config)

        from proceda.skills.parser import parse_skill

        skill = parse_skill(result)
        assert skill.name == "customer-refund"
        assert skill.step_count == 3
        # Step 2 should have APPROVAL REQUIRED marker
        step2 = skill.get_step(2)
        assert step2.requires_post_approval

    @pytest.mark.asyncio
    async def test_name_hint_passed_to_llm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When name_hint is provided, it's included in the LLM prompt."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig()

        mock_runtime = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = VALID_SKILL_WITH_NAME_HINT
        mock_response.tool_calls = []
        mock_runtime.complete.return_value = mock_response

        with patch("proceda.skills.converter.LLMRuntime", return_value=mock_runtime):
            await convert_sop("Do something.", config, name_hint="custom-name")

        # Verify the name hint was part of the user message sent to the LLM
        call_args = mock_runtime.complete.call_args
        messages = call_args[0][0]
        user_msg = next(m for m in messages if m["role"] == "user")
        assert "custom-name" in user_msg["content"]

    @pytest.mark.asyncio
    async def test_retries_on_parse_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """First LLM output is malformed, retry succeeds."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig()

        mock_runtime = AsyncMock()
        bad_response = AsyncMock()
        bad_response.content = MALFORMED_OUTPUT
        bad_response.tool_calls = []
        good_response = AsyncMock()
        good_response.content = VALID_SKILL_OUTPUT
        good_response.tool_calls = []
        mock_runtime.complete.side_effect = [bad_response, good_response]

        with patch("proceda.skills.converter.LLMRuntime", return_value=mock_runtime):
            result = await convert_sop(PLAIN_TEXT_SOP, config)

        assert mock_runtime.complete.call_count == 2
        from proceda.skills.parser import parse_skill

        skill = parse_skill(result)
        assert skill.name == "employee-onboarding"

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """All attempts produce invalid output — raises ConversionError."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig()

        mock_runtime = AsyncMock()
        bad_response = AsyncMock()
        bad_response.content = MALFORMED_OUTPUT
        bad_response.tool_calls = []
        mock_runtime.complete.return_value = bad_response

        with patch("proceda.skills.converter.LLMRuntime", return_value=mock_runtime):
            with pytest.raises(ConversionError):
                await convert_sop(PLAIN_TEXT_SOP, config)

        # 1 initial + 2 retries = 3 total
        assert mock_runtime.complete.call_count == 3

    @pytest.mark.asyncio
    async def test_strips_code_fences(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LLM wraps output in markdown code fences — they are stripped."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig()

        mock_runtime = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = FENCED_OUTPUT
        mock_response.tool_calls = []
        mock_runtime.complete.return_value = mock_response

        with patch("proceda.skills.converter.LLMRuntime", return_value=mock_runtime):
            result = await convert_sop("Do the thing.", config)

        from proceda.skills.parser import parse_skill

        skill = parse_skill(result)
        assert skill.name == "test-skill"

    @pytest.mark.asyncio
    async def test_no_api_key_raises(self) -> None:
        """No API key available raises ConversionError."""
        config = LLMConfig(api_key_env="NONEXISTENT_KEY_12345")
        with pytest.raises(ConversionError, match="API key"):
            await convert_sop("Some SOP text.", config)

    @pytest.mark.asyncio
    async def test_empty_input_raises(self) -> None:
        """Empty or whitespace-only input raises ConversionError."""
        config = LLMConfig()
        with pytest.raises(ConversionError):
            await convert_sop("", config)
        with pytest.raises(ConversionError):
            await convert_sop("   \n  ", config)
