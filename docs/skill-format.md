# Skill Format Reference

A skill is a `SKILL.md` file — a markdown document with YAML frontmatter and numbered step headings. Each skill defines one procedure for the agent to execute.

## Structure

```markdown
---
name: my-workflow
description: What this workflow does
required_tools:
  - app_name__tool_name
---

### Step 1: First step title
Instructions for this step.

### Step 2: Second step title
[APPROVAL REQUIRED]
Instructions for this step. The human must approve after it completes.

### Step 3: Third step title
[PRE-APPROVAL REQUIRED]
The human must approve before this step begins.
```

## Frontmatter

The YAML frontmatter block (between `---` markers) is required and must include:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Identifier for the skill |
| `description` | Yes | What the skill does |
| `required_tools` | No | List of MCP tool names the skill needs (format: `app__tool`) |

## Steps

Steps use `### Step N: Title` headings. Rules:

- Numbering must be sequential starting from 1
- Each step must have a title
- Step body contains natural-language instructions for the LLM
- No duplicate step numbers

## Markers

Place markers on the line immediately after the step heading.

| Marker | Effect |
|--------|--------|
| `[APPROVAL REQUIRED]` | Human must approve **after** the step completes |
| `[PRE-APPROVAL REQUIRED]` | Human must approve **before** the step begins |
| `[OPTIONAL]` | Step may be skipped by the agent |

Markers are case-insensitive. A step can have multiple markers.

## Validation

Use `proceda lint` to validate a skill file:

```bash
proceda lint ./my-skill
```

This checks for:
- Valid YAML frontmatter with required fields
- Sequential step numbering starting from 1
- Steps with empty content (warning)
- Excessive step count > 20 (warning)
- Large file size > 50KB (warning)

## Path resolution

`proceda run` accepts either:
- A directory containing a `SKILL.md` file
- A direct path to a `.md` file
