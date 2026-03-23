# Proceda

**Bring a procedure, get an agent.**

<!-- Badges -->
[![CI](https://github.com/vivekhaldar/proceda/actions/workflows/ci.yml/badge.svg)](https://github.com/vivekhaldar/proceda/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/proceda)](https://pypi.org/project/proceda/)
[![Python](https://img.shields.io/pypi/pyversions/proceda)](https://pypi.org/project/proceda/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Turn your team's Standard Operating Procedures into executable agents — without learning a framework, building a graph, or writing glue code. Proceda is a terminal-first Python SDK where a markdown file _is_ the agent definition, human approval checkpoints are declarative, and every tool connection goes through [MCP](https://modelcontextprotocol.io/).

> **SOTA on SOP-Bench** — Proceda achieves state-of-the-art on 4 of 10 runnable [SOP-Bench](https://github.com/amazon-science/SOP-Bench) domains by raw TSR (8 of 10 on SOP-consistent tasks), beating baselines set by Claude 4 Opus and Claude 4.5 Opus — often with Gemini 2.5 Flash. [Read the full report &rarr;](docs/sop-bench-results.md)

## See it work

Write a procedure:

```markdown
---
name: expense-processing
description: Process expense reports with policy validation
required_tools:
  - receipts__extract
  - erp__submit
---

### Step 1: Extract receipt data
Extract all receipt fields: date, vendor, amount, category, payment method.

### Step 2: Validate against policy
[APPROVAL REQUIRED]
Check against company policy. Flag violations.
- Single meals must not exceed $75
- Receipts older than 90 days are rejected

### Step 3: Submit to ERP
[PRE-APPROVAL REQUIRED]
Submit the approved expense report to the ERP system.
```

Run it:

```bash
proceda run ./expense-processing
```

The agent executes each step, calls tools via MCP, and pauses at the approval gates for human review. Every action is logged as a replayable JSONL event stream.

## Why Proceda

### Procedure is the source of truth

Not a prompt. Not a graph. Your SOP is the agent definition. Change the markdown, change the behavior. Non-technical teammates can read, review, and edit the procedure without touching code.

### Human-in-the-loop is structural, not bolted on

Approval gates are declared with markers like `[APPROVAL REQUIRED]` and `[PRE-APPROVAL REQUIRED]`. The runtime enforces them. You don't write approval logic — you declare where humans must be involved.

### MCP-native

Every tool connection uses the [Model Context Protocol](https://modelcontextprotocol.io/). No custom adapters, no vendor lock-in. The growing ecosystem of MCP servers — filesystem, databases, APIs, SaaS apps — is your tool library.

## How it compares

| | Proceda | LangGraph | CrewAI | AutoGen |
|---|---|---|---|---|
| Agent definition | Markdown SOP | Python graph | Python classes | Python classes |
| Human approval | Declarative markers | Custom code | Limited | Custom code |
| Tool protocol | MCP (open standard) | Custom adapters | Custom adapters | Custom adapters |
| Replay / audit | Built-in JSONL logs | Manual | No | No |
| Learning curve | Write markdown | Learn graph API | Learn framework API | Learn framework API |

## Architecture

```
SKILL.md ──→ Agent ──→ Runtime ──→ Executor ──→ LLM
                                      │
                                      ├──→ MCP Tools (stdio / HTTP)
                                      │
                                      ├──→ Human Interface (approve / clarify / recover)
                                      │
                                      └──→ Event Log (JSONL, replayable)
```

The runtime emits structured `RunEvent`s at every transition. Events drive the CLI output, event logging, and SDK callbacks.

## Install

```bash
pip install proceda
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add proceda
```

## Quickstart

1. Set your API key:

```bash
export ANTHROPIC_API_KEY=sk-...
```

2. Run one of the included examples:

```bash
proceda run ./examples/toy-greeting --config examples/toy-greeting/proceda.yaml
```

3. Configure your own tools in `proceda.yaml`:

```yaml
llm:
  model: anthropic/claude-sonnet-4-20250514

apps:
  - name: my-tools
    description: My MCP tool server
    transport: stdio
    command: ["path/to/mcp-server"]
```

See [`proceda.yaml.example`](proceda.yaml.example) for the full reference, or read the [configuration docs](docs/configuration.md).

## CLI

| Command | Description |
|---------|-------------|
| `proceda run <path>` | Run a skill interactively in the terminal |
| `proceda lint <path>` | Validate a SKILL.md file |
| `proceda replay <run-id>` | Replay a previous run from its event log |
| `proceda doctor` | Check environment (Python, config, API keys, MCP servers) |

## Python SDK

### Synchronous

```python
from proceda import Agent

agent = Agent.from_path("./my-skill")
result = agent.run()
print(result.status, result.summary)
```

### Async with event streaming

```python
from proceda import Agent

agent = Agent.from_path("./my-skill")

async for event in agent.run_stream():
    print(event.type, event.payload)
```

### Custom human interface

```python
from proceda import Agent, HumanInterface
from proceda.session import ApprovalDecision

class SlackApprover(HumanInterface):
    async def request_approval(self, request):
        # Post to Slack, wait for reaction, return decision
        return ApprovalDecision.APPROVE

    async def request_clarification(self, request):
        return "Proceed with defaults"

    async def request_error_recovery(self, request):
        return ErrorRecoveryDecision.RETRY

agent = Agent.from_path("./my-skill", human=SlackApprover())
result = await agent.run_async()
```

## Skill format

```markdown
---
name: workflow-name
description: What this workflow does
required_tools:
  - app__tool_name
---

### Step 1: Do something
Instructions for the LLM.

### Step 2: Validate
[APPROVAL REQUIRED]
Human approves after this step completes.

### Step 3: Execute
[PRE-APPROVAL REQUIRED]
Human approves before this step begins.

### Step 4: Cleanup
[OPTIONAL]
Agent may skip this step if unnecessary.
```

Full reference: [docs/skill-format.md](docs/skill-format.md)

## Examples

| Example | Runnable | Demonstrates |
|---------|----------|-------------|
| [toy-greeting](examples/toy-greeting/) | Yes | Step progression, MCP tools, pre-approval gate |
| [plan-week](examples/plan-week/) | With Google Workspace MCP | Real-world tool wiring |
| [expense-processing](examples/expense-processing/) | Illustrative | Policy validation, approval + pre-approval markers |
| [change-management](examples/change-management/) | Illustrative | Infrastructure ops, multiple approval gates, optional steps |
| [support-escalation](examples/support-escalation/) | Illustrative | Severity-based routing |

See [examples/README.md](examples/README.md) for details.

## Development

```bash
git clone https://github.com/vivekhaldar/proceda.git
cd proceda
uv sync --extra dev
make install-hooks
make check              # lint + format + test + typecheck
```

## Docs

- [Skill format reference](docs/skill-format.md)
- [Configuration reference](docs/configuration.md)
- [Architecture](docs/architecture.md)

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

Built by [Enchiridion Labs](https://enchiridionlabs.online/)
