# SOP Converter — Arbitrary SOP to SKILL.md

## Problem

Proceda requires SOPs in a strict `SKILL.md` format (YAML frontmatter + `### Step N: Title` headings + `[MARKER]` tags). Users with existing SOPs in arbitrary formats (plain text, numbered lists, wiki pages, prose documents) must manually convert them before Proceda can execute them.

The existing `auto_structure()` in `structurer.py` only handles body reformatting — it requires valid YAML frontmatter already present and just re-numbers step headings. It doesn't help with truly arbitrary input.

## Solution

A new `convert_sop()` function that uses an LLM to transform arbitrary SOP text into a complete, valid SKILL.md. Exposed via a `proceda convert` CLI command.

## Core function

```python
async def convert_sop(
    text: str,
    config: LLMConfig,
    name_hint: str | None = None,
) -> str
```

- Takes raw SOP text (any format) + LLMConfig
- Optional `name_hint` for the skill name (e.g. derived from filename)
- Returns a complete, valid SKILL.md string
- Raises `ConversionError` on failure

## LLM prompt design

The system prompt instructs the LLM to:
- Produce a complete SKILL.md with YAML frontmatter and step headings
- Generate a kebab-case `name` and concise `description`
- Break the SOP into sequential `### Step N: Title` steps
- Add `[APPROVAL REQUIRED]` where the SOP implies human sign-off or review
- Add `[PRE-APPROVAL REQUIRED]` where permission is needed before acting
- Add `[OPTIONAL]` where steps are explicitly conditional
- Infer `required_tools` if tool usage is evident, otherwise omit the field
- Preserve the substance of the original SOP — don't drop information
- Output ONLY the SKILL.md content, no explanation or wrapping

## Validation loop

LLMs sometimes produce slightly malformed output. The converter uses a retry loop:

1. Call LLM to get SKILL.md output
2. Strip any markdown code fences the LLM might wrap it in
3. Run `parse_skill()` on the result
4. If parse fails, feed the error back to the LLM as a follow-up message and retry
5. Up to 2 retries (3 total attempts). If all fail, raise `ConversionError`.

## CLI command

```
proceda convert <input> [--output PATH] [--name HINT] [--stdout]
```

- `input`: Path to SOP file, or `-` for stdin
- `--output` / `-o`: Write to this path (default: `./SKILL.md`)
- `--name`: Optional name hint
- `--stdout`: Print to stdout instead of writing a file

## Relationship to `auto_structure()`

`auto_structure()` stays as-is for the loader path (content with frontmatter but malformed step headings). `convert_sop()` is the full pipeline for truly arbitrary input. Both use `LLMRuntime` and `parse_skill()` but are otherwise independent.

## Files

- `src/proceda/skills/converter.py` — Core conversion logic
- `src/proceda/cli/commands/convert.py` — CLI command
- `src/proceda/exceptions.py` — `ConversionError` addition
- `src/proceda/cli/main.py` — Command registration
- `tests/test_skills/test_converter.py` — Tests
