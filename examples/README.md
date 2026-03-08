# Examples

## Runnable

### toy-greeting

A simple 5-step workflow demonstrating step progression, tool use, and a `[PRE-APPROVAL REQUIRED]` gate. Includes a real MCP server (`time_left_server.py`) and a Python SDK script (`run.py`).

```bash
# From the repo root:
export ANTHROPIC_API_KEY=...
proceda run ./examples/toy-greeting
```

Or use the SDK directly:

```bash
uv run python examples/toy-greeting/run.py
```

### plan-week

Weekly planning workflow using Google Workspace tools (Calendar, Drive). Requires a configured Google Workspace MCP server.

## Illustrative

These examples show realistic SKILL.md structures for enterprise use cases. They reference fictional tool servers — use them as templates for your own skills.

### expense-processing

Three-step expense report workflow with policy validation and ERP submission. Demonstrates `[APPROVAL REQUIRED]` (post-step) and `[PRE-APPROVAL REQUIRED]` (pre-step) markers.

### change-management

Infrastructure change management with risk assessment, approval gates, and rollback planning.

### support-escalation

Customer support ticket routing based on severity, with escalation and SLA tracking.
