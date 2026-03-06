"""Auto-structure arbitrary markdown into SKILL.md step format."""
# ABOUTME: Reformats markdown content into ### Step N: Title headings using an LLM
# ABOUTME: when the content doesn't already follow the required format.

from __future__ import annotations

import logging
import re

from proceda.config import LLMConfig
from proceda.exceptions import SkillParseError
from proceda.llm.runtime import LLMRuntime
from proceda.skills.parser import _parse_frontmatter, _parse_steps

logger = logging.getLogger(__name__)

_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

_STRUCTURE_PROMPT = """\
You are a document formatter. Your job is to restructure the markdown body \
of a skill file into numbered step headings.

Rules:
- Convert each logical section into a heading of the form: ### Step N: Title
- Preserve ALL content verbatim — do not add, remove, or rephrase anything
- Number steps sequentially starting from 1
- Only output the restructured body (no frontmatter, no explanation)
- If the content already has numbered sections (like "# 1. Title" or "## Step 1"), \
convert them to the ### Step N: Title format
"""


async def auto_structure(content: str, config: LLMConfig) -> str:
    """Try parsing content; if no valid steps, use LLM to restructure.

    Returns the original content if:
    - Content already parses successfully
    - No frontmatter is present (can't restructure without it)
    - No API key is available
    - LLM call fails
    """
    # Try parsing as-is
    try:
        _parse_frontmatter(content)
    except SkillParseError:
        return content

    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        return content

    frontmatter_str = content[: match.end()]
    body = content[match.end() :]

    # Check if steps already parse
    try:
        _parse_steps(body)
        return content
    except SkillParseError:
        pass

    # No valid steps — try LLM restructuring
    # Skip if model requires an API key and none is set.
    # Local models (e.g. ollama) don't need one.
    needs_api_key = not config.model.startswith("ollama")
    if needs_api_key and not config.api_key:
        logger.debug("No API key available, skipping auto-structure")
        return content

    try:
        llm = LLMRuntime(config)
        messages = [
            {"role": "system", "content": _STRUCTURE_PROMPT},
            {"role": "user", "content": body},
        ]
        response = await llm.complete(messages)
        if response.content:
            restructured = frontmatter_str + response.content
            # Verify the result actually parses
            try:
                _parse_steps(response.content)
                logger.info("Auto-structured content into valid step format")
                return restructured
            except SkillParseError:
                logger.warning("LLM output still doesn't parse, using original")
                return content
        return content
    except Exception:
        logger.warning("Auto-structure LLM call failed, using original content", exc_info=True)
        return content
