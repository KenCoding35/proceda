# Proceda

Turn SOPs into runnable agents with built-in human oversight.

## Install

```bash
pip install proceda
```

## Quickstart

```bash
export ANTHROPIC_API_KEY=...
proceda run ./examples/expense-processing
```

## What is Proceda?

Proceda is a terminal-first, Python-native SDK for turning Standard Operating Procedures (SOPs) into runnable agents. Write a `SKILL.md`, attach tools via MCP, and run it from the terminal with human approval checkpoints built in.

## Usage

### Write a skill

```markdown
---
name: my-workflow
description: Automate a workflow with human checkpoints
required_tools:
  - my_app__tool_name
---

### Step 1: Gather data
Use the tool to gather the required data.

### Step 2: Validate
[APPROVAL REQUIRED]
Validate the data against policy.

### Step 3: Submit
[PRE-APPROVAL REQUIRED]
Submit the validated data.
```

### Run it

```bash
# Interactive terminal mode
proceda run ./my-skill

# Full-screen TUI dev mode
proceda dev ./my-skill

# Validate a skill
proceda lint ./my-skill

# Replay a previous run
proceda replay .proceda/runs/<run-id>

# Check your environment
proceda doctor
```

### Use as a Python SDK

```python
from proceda import Agent

agent = Agent.from_path("./my-skill")
result = agent.run()
print(result.status)
```

### Event-driven usage

```python
from proceda import Agent

agent = Agent.from_path("./my-skill")

async for event in agent.run_stream():
    print(event.type, event.payload)
```

### Custom human interface

```python
from proceda import Agent, HumanInterface

class MyHuman(HumanInterface):
    async def request_approval(self, request):
        return ApprovalDecision.APPROVE

    async def request_clarification(self, request):
        return "Proceed"

agent = Agent.from_path("./my-skill", human=MyHuman())
result = agent.run()
```

## Development

### Setup

```bash
uv sync --extra dev
make install-hooks
```

### Pre-commit hooks

Every commit automatically runs:
- **ruff format** — auto-formats Python files
- **ruff check** — lints and auto-fixes; aborts commit if fixes were applied so you can review
- **pytest** — full test suite (~1s)

### Makefile targets

| Target | Description |
|--------|-------------|
| `make lint` | Run ruff linter |
| `make format` | Run ruff formatter |
| `make test` | Run pytest |
| `make typecheck` | Run mypy (strict mode) |
| `make check` | Run all of the above |
| `make install-hooks` | Install pre-commit hooks |

## License

MIT
