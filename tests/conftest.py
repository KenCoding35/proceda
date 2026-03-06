"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from skillrunner.skill import Skill

SAMPLE_SKILL_CONTENT = """\
---
name: test-skill
description: A test skill for unit tests
required_tools:
  - test__tool_a
  - test__tool_b
---

### Step 1: First step
Do the first thing.

### Step 2: Second step with approval
[APPROVAL REQUIRED]
Do the second thing and get approval.

### Step 3: Third step with pre-approval
[PRE-APPROVAL REQUIRED]
Do the third thing after getting pre-approval.

### Step 4: Optional step
[OPTIONAL]
This step is optional.
"""

MINIMAL_SKILL_CONTENT = """\
---
name: minimal-skill
description: A minimal test skill
---

### Step 1: Only step
Do the only thing.
"""

MALFORMED_SKILL_NO_FRONTMATTER = """\
### Step 1: No frontmatter
This skill has no frontmatter.
"""

MALFORMED_SKILL_NO_NAME = """\
---
description: Missing name field
---

### Step 1: A step
Content.
"""

MALFORMED_SKILL_NO_STEPS = """\
---
name: no-steps
description: This skill has no steps
---

Just some text without any step headings.
"""

MALFORMED_SKILL_DUPLICATE_STEPS = """\
---
name: duplicate-steps
description: Duplicate step numbers
---

### Step 1: First
Content.

### Step 1: Duplicate
Content.
"""

MALFORMED_SKILL_NONSEQUENTIAL = """\
---
name: nonsequential
description: Non-sequential step numbers
---

### Step 1: First
Content.

### Step 3: Third
Content.
"""


@pytest.fixture
def sample_skill_content() -> str:
    return SAMPLE_SKILL_CONTENT


@pytest.fixture
def minimal_skill_content() -> str:
    return MINIMAL_SKILL_CONTENT


@pytest.fixture
def sample_skill() -> Skill:
    from skillrunner.skills.parser import parse_skill

    return parse_skill(SAMPLE_SKILL_CONTENT)


@pytest.fixture
def minimal_skill() -> Skill:
    from skillrunner.skills.parser import parse_skill

    return parse_skill(MINIMAL_SKILL_CONTENT)


@pytest.fixture
def tmp_skill_dir(tmp_path: Path, sample_skill_content: str) -> Path:
    """Create a temporary directory with a SKILL.md file."""
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(sample_skill_content)
    return tmp_path


@pytest.fixture
def tmp_skill_file(tmp_path: Path, sample_skill_content: str) -> Path:
    """Create a temporary SKILL.md file."""
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(sample_skill_content)
    return skill_file
