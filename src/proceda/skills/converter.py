# ABOUTME: Converts arbitrary SOP text into valid SKILL.md format using an LLM.
# ABOUTME: Handles retries with parse error feedback and code fence stripping.

from __future__ import annotations

import logging
import re

from proceda.config import LLMConfig
from proceda.exceptions import ConversionError
from proceda.llm.runtime import LLMRuntime
from proceda.skills.parser import parse_skill

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

_CONVERT_PROMPT = """\
You are a document converter. Your job is to convert an arbitrary Standard \
Operating Procedure (SOP) into Proceda's SKILL.md format.

Output a complete SKILL.md file with this exact structure:

---
name: kebab-case-name
description: A concise one-line description of what this SOP does
required_tools:
  - tool_name  # Only if the SOP references specific tools; omit this field entirely otherwise
---

### Step 1: Title
Step instructions here.

### Step 2: Title
More instructions.

Rules:
- The YAML frontmatter MUST start with --- on the first line and end with --- on its own line
- Generate a kebab-case `name` derived from the SOP's title or purpose
- Write a concise `description` (one sentence)
- Break the SOP into sequential steps using `### Step N: Title` headings (N starts at 1)
- Each step title should be a short, imperative phrase
- Preserve the substance of the original SOP in the step bodies — do not drop information
- Add `[APPROVAL REQUIRED]` on its own line after the step heading where the SOP implies \
human sign-off, review, verification, or approval after the step completes
- Add `[PRE-APPROVAL REQUIRED]` where the SOP implies getting permission before acting
- Add `[OPTIONAL]` where steps are explicitly conditional or optional
- Only include `required_tools` if the SOP explicitly references specific tools or systems \
that map to MCP tool names; otherwise omit the field entirely
- Output ONLY the SKILL.md content — no explanation, no wrapping, no code fences
"""

_CODE_FENCE_PATTERN = re.compile(
    r"^```(?:markdown|md|yaml)?\s*\n(.*?)```\s*$",
    re.DOTALL,
)


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences that LLMs sometimes wrap output in."""
    stripped = text.strip()
    match = _CODE_FENCE_PATTERN.match(stripped)
    if match:
        return match.group(1).strip()
    return stripped


async def convert_sop(
    text: str,
    config: LLMConfig,
    name_hint: str | None = None,
) -> str:
    """Convert arbitrary SOP text into valid SKILL.md format using an LLM.

    Returns the complete SKILL.md content as a string.
    Raises ConversionError if conversion fails after retries.
    """
    if not text or not text.strip():
        raise ConversionError("Input SOP text is empty")

    needs_api_key = not config.model.startswith("ollama")
    if needs_api_key and not config.api_key:
        raise ConversionError(f"API key not set (expected env var: {config.api_key_env})")

    llm = LLMRuntime(config)

    user_content = text
    if name_hint:
        user_content = f"Suggested skill name: {name_hint}\n\n{text}"

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _CONVERT_PROMPT},
        {"role": "user", "content": user_content},
    ]

    last_error: Exception | None = None

    for attempt in range(1 + MAX_RETRIES):
        try:
            response = await llm.complete(messages)
        except Exception as e:
            raise ConversionError(f"LLM call failed: {e}") from e

        if not response.content:
            last_error = ConversionError("LLM returned empty response")
            continue

        cleaned = _strip_code_fences(response.content)

        try:
            parse_skill(cleaned)
            logger.info("SOP converted to valid SKILL.md on attempt %d", attempt + 1)
            return cleaned
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                logger.info(
                    "Conversion attempt %d failed to parse: %s — retrying",
                    attempt + 1,
                    e,
                )
                messages.append({"role": "assistant", "content": response.content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"That output failed validation with this error:\n{e}\n\n"
                            "Please fix the issue and output the corrected SKILL.md. "
                            "Output ONLY the SKILL.md content, nothing else."
                        ),
                    }
                )

    raise ConversionError(
        f"Failed to produce valid SKILL.md after {1 + MAX_RETRIES} attempts: {last_error}"
    )
