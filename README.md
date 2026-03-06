# SkillRunner

Turn SOPs into runnable agents with built-in human oversight.

## Install

```bash
pip install skillrunner
```

## Quickstart

```bash
export ANTHROPIC_API_KEY=...
skillrunner run ./examples/expense-processing
```

## What is SkillRunner?

SkillRunner is a terminal-first, Python-native SDK for turning Standard Operating Procedures (SOPs) into runnable agents. Write a `SKILL.md`, attach tools via MCP, and run it from the terminal with human approval checkpoints built in.

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
skillrunner run ./my-skill

# Full-screen TUI dev mode
skillrunner dev ./my-skill

# Validate a skill
skillrunner lint ./my-skill

# Replay a previous run
skillrunner replay .skillrunner/runs/<run-id>

# Check your environment
skillrunner doctor
```

### Use as a Python SDK

```python
from skillrunner import Agent

agent = Agent.from_path("./my-skill")
result = agent.run()
print(result.status)
```

### Event-driven usage

```python
from skillrunner import Agent

agent = Agent.from_path("./my-skill")

async for event in agent.run_stream():
    print(event.type, event.payload)
```

### Custom human interface

```python
from skillrunner import Agent, HumanInterface

class MyHuman(HumanInterface):
    async def request_approval(self, request):
        return ApprovalDecision.APPROVE

    async def request_clarification(self, request):
        return "Proceed"

agent = Agent.from_path("./my-skill", human=MyHuman())
result = agent.run()
```

## License

MIT
