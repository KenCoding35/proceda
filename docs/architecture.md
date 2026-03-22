# Proceda OSS SDK Technical Design

**Version**: 0.1.0  
**Status**: Draft  
**Last Updated**: 2026-03-05  
**Audience**: Engineering  
**Primary Goal**: Provide an implementation-grade design for extracting the Proceda runtime into a standalone Python SDK + CLI/TUI repo

---

## Table of Contents

1. [Overview](#1-overview)
2. [Goals and Non-Goals](#2-goals-and-non-goals)
3. [Design Decisions](#3-design-decisions)
4. [Target Repository Shape](#4-target-repository-shape)
5. [Architecture Overview](#5-architecture-overview)
6. [Core Runtime Model](#6-core-runtime-model)
7. [Package and Module Design](#7-package-and-module-design)
8. [Detailed Data Model](#8-detailed-data-model)
9. [Event Model](#9-event-model)
10. [Public Python API](#10-public-python-api)
11. [CLI Design](#11-cli-design)
12. [TUI Design](#12-tui-design)
13. [Skill Loading and Parsing](#13-skill-loading-and-parsing)
14. [LLM Runtime Design](#14-llm-runtime-design)
15. [MCP Integration Design](#15-mcp-integration-design)
16. [Human Interface Design](#16-human-interface-design)
17. [Logging, Replay, and Persistence](#17-logging-replay-and-persistence)
18. [Config Design](#18-config-design)
19. [Extraction Map From Current Repo](#19-extraction-map-from-current-repo)
20. [Implementation Plan](#20-implementation-plan)
21. [Detailed Task Breakdown](#21-detailed-task-breakdown)
22. [Testing Plan](#22-testing-plan)
23. [Release Plan](#23-release-plan)
24. [Appendix: Acceptance Criteria](#24-appendix-acceptance-criteria)

---

## 1. Overview

This document describes how to extract the existing Proceda execution kernel from the current full-stack repository and turn it into a standalone open-source SDK.

The target product is:

- one Python package
- one CLI
- one terminal-first user experience
- one coherent public runtime model

The target product is not:

- a FastAPI backend
- a React frontend
- a multi-tenant cloud service
- a collection of loosely-related internal packages

The implementation goal is not to preserve the current code layout. The implementation goal is to preserve and improve the runtime semantics while dramatically improving product shape and developer experience.

---

## 2. Goals and Non-Goals

### 2.1 Goals

- Extract the skill parser, runtime, MCP integration, and session model into a standalone SDK.
- Replace the WebSocket/web-API coordination model with an internal event stream.
- Provide a polished CLI and terminal UI.
- Preserve the current approval, clarification, tool-call, and step-execution semantics.
- Preserve local-first execution.
- Make the runtime embeddable from Python.

### 2.2 Non-Goals

- Browser UI parity with the hosted product
- Auth/SSO
- Team collaboration
- Hosted persistence
- Billing
- Enterprise admin features

---

## 3. Design Decisions

This section records the major design decisions and why they were chosen.

### 3.1 Python-First

**Decision**: Implement the OSS SDK in Python only.

**Rationale**:

- Existing runtime already exists in Python.
- Python is the strongest fit for the target audience.
- Avoids losing momentum to a full rewrite.

### 3.2 One Package, Not Many

**Decision**: Publish one package, `proceda`.

**Rationale**:

- Stronger product story
- Lower cognitive overhead
- Easier install and adoption
- Avoids turning a simple concept into internal package sprawl

### 3.3 Event Stream Instead of WebSocket Coordinator

**Decision**: Replace WebSocket-first coordination with in-process runtime events.

**Rationale**:

- CLI and TUI need local event subscriptions, not socket transport
- Events are a better primitive for replay, embedding, and later web adapters
- Decouples runtime from delivery mechanism

### 3.4 Terminal-Only v1

**Decision**: Do not support HTML widget rendering in v1 OSS.

**Rationale**:

- Terminal focus is strategically cleaner
- Browser UI is part of the hosted value proposition
- HTML rendering creates disproportionate complexity

### 3.5 Event Log in v1, Resume in v2

**Decision**: v1 includes append-only local event logging and replay, but not full session resume.

**Rationale**:

- Replay is high value for debugging and demos
- Full resume requires tighter snapshot semantics
- This keeps v1 implementation tractable without sacrificing observability

### 3.6 Preserve `SKILL.md`

**Decision**: Continue using `SKILL.md` as the canonical authoring format.

**Rationale**:

- It is already implemented and understood
- It matches the product thesis
- It avoids inventing an unnecessary DSL

---

## 4. Target Repository Shape

The new repository should look like this:

```text
proceda/
  pyproject.toml
  README.md
  LICENSE
  .gitignore
  src/
    proceda/
      __init__.py
      agent.py
      skill.py
      session.py
      events.py
      runtime.py
      config.py
      exceptions.py
      logging.py
      human.py
      replay.py
      cli/
        __init__.py
        main.py
        commands/
          run.py
          dev.py
          lint.py
          replay.py
          doctor.py
      tui/
        __init__.py
        app.py
        screens.py
        widgets.py
        bindings.py
      llm/
        __init__.py
        runtime.py
        prompts.py
        tool_schemas.py
      mcp/
        __init__.py
        client.py
        orchestrator.py
        models.py
      skills/
        __init__.py
        parser.py
        loader.py
        registry.py
      store/
        __init__.py
        event_log.py
        snapshots.py
      internal/
        executor.py
        context.py
        summary.py
        tool_executor.py
  examples/
  tests/
  docs/
```

### 4.1 Important Rule

Do not carry over the current `backend/` and `frontend/` directory structure. That shape reflects the hosted product, not the new SDK.

---

## 5. Architecture Overview

At a high level, the runtime architecture should be:

```text
                +-------------------+
                |   CLI / TUI / SDK |
                +---------+---------+
                          |
                          v
                +-------------------+
                |   Agent / Run API |
                +---------+---------+
                          |
                          v
                +-------------------+
                |  Runtime Engine    |
                |  - step execution  |
                |  - session state   |
                |  - event emission  |
                +----+----------+---+
                     |          |
                     v          v
             +----------+   +---------+
             | LLM      |   | MCP     |
             | Runtime  |   | Tools   |
             +----------+   +---------+
                     |
                     v
               +-----------+
               | Event Log |
               +-----------+
```

### 5.1 Primary Runtime Flow

1. Load config
2. Resolve skill
3. Build `Agent`
4. Create `RunSession`
5. Start runtime loop
6. Emit events as execution progresses
7. Drive terminal UI or SDK callbacks from events
8. Persist events locally
9. Produce final `RunResult`

---

## 6. Core Runtime Model

The new repo should revolve around four public concepts:

- `Skill`
- `Agent`
- `RunSession`
- `RunEvent`

### 6.1 `Skill`

Represents parsed `SKILL.md` content.

Responsibilities:

- hold metadata
- hold steps
- preserve raw content
- expose helper methods for step lookup and validation

### 6.2 `Agent`

High-level wrapper around a `Skill` plus runtime configuration.

Responsibilities:

- create sessions
- expose convenient `run()` APIs
- own references to config, LLM runtime, tool executor

### 6.3 `RunSession`

Represents one execution of an `Agent`.

Responsibilities:

- hold mutable state
- emit events
- interact with human interface
- execute and finalize the run

### 6.4 `RunEvent`

The canonical transport-independent record of everything important that happens.

Responsibilities:

- feed the TUI
- feed logs
- feed replay
- provide a future bridge for web adapters

---

## 7. Package and Module Design

This section defines the target role of each major module.

### 7.1 `proceda.agent`

Public high-level entry points.

Expected contents:

- `Agent`
- helper constructors such as `Agent.from_path()`

Responsibilities:

- create configured agent objects
- provide ergonomic top-level methods

### 7.2 `proceda.skill`

Public skill-facing data models.

Expected contents:

- `Skill`
- `SkillStep`
- `StepMarker`

### 7.3 `proceda.session`

Public session-facing data models.

Expected contents:

- `RunSession`
- `RunStatus`
- `RunResult`
- `ApprovalRequest`
- `ClarificationRequest`
- `ToolCall`

### 7.4 `proceda.events`

Public event model.

Expected contents:

- event enums or tagged unions
- event payload models
- event serialization helpers

### 7.5 `proceda.runtime`

Public orchestration API for starting and controlling runs.

Expected contents:

- `Runtime`
- `RunHandle`

### 7.6 `proceda.human`

Human interface contracts.

Expected contents:

- `HumanInterface` protocol
- `TerminalHumanInterface`
- `AutoApproveHumanInterface` for tests

### 7.7 `proceda.llm`

LLM wrapper layer.

Expected contents:

- current LiteLLM wrapper
- control tool schema helpers
- provider-specific normalization

### 7.8 `proceda.mcp`

MCP communication layer.

Expected contents:

- client transports
- orchestrator
- MCP data models

### 7.9 `proceda.skills`

Skill discovery and parsing.

Expected contents:

- parser
- local loader
- registry or path resolver

### 7.10 `proceda.store`

Local logging and later persistence.

Expected contents:

- JSONL event log writer
- run directory manager
- v2 snapshot support

### 7.11 `proceda.tui`

Textual-based terminal UI.

Expected contents:

- `ProcedaApp`
- live widgets
- approval/clarification prompts
- event-driven screens

### 7.12 `proceda.internal`

Internal runtime pieces that should not be marketed as public API.

Expected contents:

- executor
- context management
- summary generation
- adapter helpers

This internal namespace is important. It gives implementation freedom without polluting the public surface.

---

## 8. Detailed Data Model

### 8.1 `Skill`

Required fields:

- `id: str`
- `name: str`
- `description: str`
- `path: Path | None`
- `source_url: str | None`
- `raw_content: str`
- `steps: list[SkillStep]`
- `required_tools: list[str] | None`

### 8.2 `SkillStep`

Required fields:

- `index: int`
- `title: str`
- `content: str`
- `markers: list[StepMarker]`

Derived properties:

- `requires_pre_approval`
- `requires_post_approval`
- `is_optional`

### 8.3 `RunStatus`

Allowed values:

- `created`
- `running`
- `awaiting_approval`
- `awaiting_input`
- `suspended`
- `completed`
- `failed`
- `cancelled`

### 8.4 `ToolCall`

Required fields:

- `id: str`
- `name: str`
- `arguments: dict[str, Any]`

### 8.5 `ApprovalRequest`

Required fields:

- `step_index: int`
- `step_title: str`
- `approval_type: Literal["pre_step", "post_step"]`
- `context: str`
- `pending_tool_calls: list[ToolCall]`
- `tool_results: list[dict[str, Any]]`

### 8.6 `ClarificationRequest`

Required fields:

- `question: str`
- `options: list[str]`
- `context: str | None`

### 8.7 `RunSession`

This should be the authoritative mutable session state.

Required fields:

- `id: str`
- `skill_id: str`
- `skill_name: str`
- `status: RunStatus`
- `current_step: int`
- `messages: list[RunMessage]`
- `pending_approval: ApprovalRequest | None`
- `pending_clarification: ClarificationRequest | None`
- `pending_error: ErrorContext | None`
- `pending_tool_calls: list[ToolCall]`
- `step_tool_results: list[dict[str, Any]]`
- `approval_records: list[ApprovalRecord]`
- `created_at: datetime`
- `started_at: datetime | None`
- `completed_at: datetime | None`
- `last_activity_at: datetime`

### 8.8 `RunMessage`

Use a role-based message model internally, similar to the current implementation.

Required fields:

- `id: str`
- `role: Literal["system", "assistant", "user", "tool"]`
- `content: str`
- `timestamp: datetime`
- `tool_call_id: str | None`
- `app_name: str | None`
- `tool_calls: list[ToolCall] | None`

### 8.9 `RunResult`

Required fields:

- `session_id: str`
- `status: RunStatus`
- `summary: str`
- `completed_steps: int`
- `failed_step: int | None`
- `event_log_path: Path`
- `prompt_tokens: int`
- `completion_tokens: int`
- `total_tokens: int`

---

## 9. Event Model

The event model is the central architectural change from the current repo.

### 9.1 Design Rule

Every meaningful runtime transition must emit a structured `RunEvent`.

### 9.2 Event Categories

#### Lifecycle Events

- `run.created`
- `run.started`
- `run.completed`
- `run.failed`
- `run.cancelled`

#### Step Events

- `step.started`
- `step.completed`
- `step.skipped`

#### Message Events

- `message.system`
- `message.assistant`
- `message.user`
- `message.tool`
- `message.reasoning`

#### Tool Events

- `tool.called`
- `tool.completed`
- `tool.failed`

#### Human Events

- `approval.requested`
- `approval.responded`
- `clarification.requested`
- `clarification.responded`
- `error.recovery_requested`
- `error.recovery_selected`

#### LLM Usage Events

- `llm.usage` — emitted after each LLM call with `prompt_tokens`, `completion_tokens`, `total_tokens`, and cumulative counters

#### Runtime State Events

- `status.changed`
- `context.updated`
- `summary.generated`

### 9.3 Event Base Shape

All events should serialize as:

```json
{
  "id": "evt_123",
  "timestamp": "2026-03-05T18:00:00Z",
  "run_id": "run_123",
  "type": "tool.called",
  "payload": {
    "tool_name": "erp__submit",
    "arguments": {"amount": 100}
  }
}
```

### 9.4 Event Payload Rules

- Payloads must be JSON-serializable.
- Event names must be stable once released.
- Sensitive values should be redacted before persistence when configured.

### 9.5 Event Consumers

Event consumers include:

- TUI renderer
- non-interactive CLI printer
- event log writer
- replay engine
- SDK callbacks

### 9.6 Event Emission API

Define a simple internal emitter interface:

```python
class EventSink(Protocol):
    async def handle(self, event: RunEvent) -> None: ...
```

Support composition:

- `CompositeEventSink([tui_sink, log_sink, callback_sink])`

This replaces the current WebSocket-specific emitter.

---

## 10. Public Python API

The public Python API must be deliberately small.

### 10.1 High-Level API

```python
from proceda import Agent

agent = Agent.from_path("./skills/expense-processing")
result = agent.run()
print(result.status)
```

### 10.2 Async/Event API

```python
from proceda import Agent

agent = Agent.from_path("./skills/expense-processing")
session = agent.create_session()

async for event in session.run_stream():
    print(event.type, event.payload)
```

### 10.3 Custom Human Interface Example

```python
from proceda import Agent, HumanInterface

class MyHuman(HumanInterface):
    async def request_approval(self, request):
        return True

    async def request_clarification(self, request):
        return "Proceed with option A"

agent = Agent.from_path("./skills/example", human=MyHuman())
result = agent.run()
```

### 10.4 Public API Stability Rule

Only export a minimal curated set from `proceda.__init__`.

Do not export internal executor implementation details.

---

## 11. CLI Design

### 11.1 Framework Choice

Use `typer` for the CLI.

Rationale:

- good help output
- strong type annotations
- easy subcommand organization

### 11.2 Command Structure

```text
proceda run <path>
proceda dev <path>
proceda lint <path>
proceda replay <run-id-or-path>
proceda doctor
```

### 11.3 Command Behavior

#### `run`

- interactive terminal mode
- not full-screen
- prompts inline
- writes event log
- prints final summary

#### `dev`

- launches Textual app
- full-screen
- richer introspection

#### `lint`

- parse and validate
- report warnings/errors
- exit non-zero on errors

#### `replay`

- read event log
- render events in order
- no external side effects

#### `doctor`

- environment diagnostics
- config diagnostics
- MCP diagnostics

### 11.4 Exit Codes

Use stable exit codes:

- `0` success
- `1` runtime failure
- `2` config or validation error
- `3` user rejection / cancellation
- `4` environment or dependency error

---

## 12. TUI Design

### 12.1 Framework Choice

Use `textual`.

Rationale:

- modern Python terminal UI framework
- supports layouts, widgets, async events
- good polish potential

### 12.2 TUI Architecture

The TUI should subscribe to runtime events rather than call runtime internals directly.

This means:

- runtime remains testable outside Textual
- replay can drive the same UI
- future web adapters can reuse the event model

### 12.3 Required Widgets

- `SkillHeaderWidget`
- `StepListWidget`
- `MessageStreamWidget`
- `ToolActivityWidget`
- `StatusBarWidget`
- `ApprovalModal`
- `ClarificationModal`

### 12.4 State Management

The TUI should maintain a derived `ViewState` built from runtime events.

Do not let the TUI mutate the session state directly.

### 12.5 HTML/UI Resource Handling

In v1:

- if an MCP tool returns HTML or UI resources, capture them as an artifact event
- show a short message such as "HTML UI resource returned; terminal rendering not supported"
- store the raw content path in the run directory if feasible

This preserves data without committing to widget rendering.

---

## 13. Skill Loading and Parsing

### 13.1 Loader Rules

Support these path forms in v1:

- path to `SKILL.md`
- path to a directory containing `SKILL.md`

Do not support remote URLs in v1.

### 13.2 Parser Rules

Reuse the existing parser logic where possible, but move it under `proceda.skills.parser`.

The parser must:

- read frontmatter
- extract step headings
- detect markers
- preserve raw content
- raise typed errors on invalid structure

### 13.3 Linting Rules

Linting should include:

- missing frontmatter fields
- no steps found
- malformed step headings
- duplicate or invalid step numbering
- unresolved `required_tools` when the environment is fully configured

Warnings may include:

- no `required_tools`
- skill too large
- too many steps

---

## 14. LLM Runtime Design

### 14.1 Reuse Strategy

The current LiteLLM-based wrapper should be adapted, not rewritten from scratch.

Source reference:

- `backend/src/proceda/engine/llm_runtime.py`

### 14.2 Required Features

- provider/model abstraction
- control tools
- parsing tool calls into internal models
- retry behavior
- provider-specific compatibility adjustments

### 14.3 Control Tools

v1 must support:

- `complete_step`
- `request_clarification`

These should remain runtime-native and always be injected.

### 14.4 Prompt Construction

The runtime should continue to use:

- skill context
- current step instructions
- prior messages
- tool schemas

The prompt construction logic should be isolated from the CLI/TUI.

### 14.5 Reasoning

If reasoning traces are exposed by the current model or via `<thinking>` tags, treat them as events:

- `message.reasoning`

The runtime should not assume the TUI always displays them.

---

## 15. MCP Integration Design

### 15.1 Reuse Strategy

Adapt the current MCP client and app orchestrator:

- `backend/src/proceda/engine/mcp_client.py`
- `backend/src/proceda/engine/app_orchestrator.py`

### 15.2 v1 Requirements

- stdio MCP transport
- HTTP MCP transport
- tool discovery
- tool invocation
- tool result parsing
- optional resource fetching

### 15.3 Tool Access Rules

Enforce:

- global denylist
- skill `required_tools` allowlist
- tool existence checks

### 15.4 Logging

MCP traffic should emit events:

- `tool.called`
- `tool.completed`
- `tool.failed`
- optional lower-level MCP debug events when dev mode is on

### 15.5 Design Rule

The runtime should not know about WebSocket payloads or frontend display types. MCP results should be converted into internal events and messages only.

---

## 16. Human Interface Design

### 16.1 Human Interface Protocol

Define:

```python
class HumanInterface(Protocol):
    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision: ...
    async def request_clarification(self, request: ClarificationRequest) -> ClarificationAnswer: ...
    async def request_error_recovery(self, request: ErrorRecoveryRequest) -> ErrorRecoveryDecision: ...
```

### 16.2 Default Implementations

Implement:

- `TerminalHumanInterface`
- `TextualHumanInterface`
- `AutoApproveHumanInterface` for tests

### 16.3 Design Rule

The executor should request human input through the `HumanInterface`, not by directly reading stdin or calling TUI methods.

This is essential for:

- embedding
- testing
- replay
- future extensions

### 16.4 Approval Semantics

#### Pre-Step Approval

Pause when a step requires pre-approval and app tool calls are about to occur.

#### Post-Step Approval

Pause after the step has been completed and before advancing.

#### Rejection Behavior

If a user rejects:

- default behavior is session cancellation unless a future policy says otherwise
- the event log must record the rejection

For v1, rejection should end the run with a clear status and summary.

---

## 17. Logging, Replay, and Persistence

### 17.1 v1 Event Log

Every run should create a run directory:

```text
.proceda/runs/<timestamp>_<short-id>/
```

Contents:

```text
events.jsonl
metadata.json
summary.txt
artifacts/
```

### 17.2 `events.jsonl`

Each line is one serialized `RunEvent`.

Requirements:

- append-only
- flush regularly
- deterministic ordering

### 17.3 Replay

The replay command should:

- load `metadata.json`
- stream `events.jsonl`
- render events using the same or similar view layer

### 17.4 v2 Snapshots

Add:

```text
snapshot.json
```

Checkpoint timing:

- after step completion
- when entering approval/clarification waits
- on clean shutdown when possible

### 17.5 Resume Rules for v2

- Resume only from trusted local snapshots.
- Rehydrate session state.
- Restore pending approval or clarification if present.
- Never silently replay external side effects.
- If state is ambiguous, fail closed and explain why.

---

## 18. Config Design

### 18.1 Config File Name

Default:

```text
proceda.yaml
```

### 18.2 Config Model

Keep a simplified version of the current config model:

- `llm`
- `apps`
- `dev`
- `security`
- `logging`

Drop hosted-only config sections from the new repo.

### 18.3 Config Search Order

1. `--config` path if provided
2. `./proceda.yaml`
3. `~/.config/proceda/config.yaml`

### 18.4 Environment Expansion

Preserve `${VAR}` and `${VAR:-default}` expansion support.

---

## 19. Extraction Map From Current Repo

This section maps the current implementation to the target repo.

### 19.1 Keep and Adapt

These files are strong extraction candidates:

- `backend/src/proceda/engine/skill_parser.py`
- `backend/src/proceda/engine/executor.py`
- `backend/src/proceda/engine/llm_runtime.py`
- `backend/src/proceda/engine/mcp_client.py`
- `backend/src/proceda/engine/app_orchestrator.py`
- `backend/src/proceda/engine/context_manager.py`
- `backend/src/proceda/engine/summary.py`
- `backend/src/proceda/models/skill.py`
- `backend/src/proceda/models/session.py`
- `backend/src/proceda/models/mcp.py`
- `backend/src/proceda/models/config.py`

### 19.2 Remove Entirely

These should not move into the OSS SDK:

- `backend/src/proceda/api/routes.py`
- `backend/src/proceda/api/websocket.py`
- `backend/src/proceda/api/auth.py`
- `backend/src/proceda/api/scalekit_auth.py`
- `frontend/`
- deployment and cloud-specific scripts

### 19.3 Replace

These need conceptual replacement:

| Current | Replace With |
|--------|---------------|
| WebSocketEventEmitter | generic `EventSink` |
| ExecutionCoordinator | `Runtime` + `RunSession` + event pipeline |
| FastAPI entrypoint | Typer CLI + Textual app |
| frontend display models | TUI `ViewState` derived from runtime events |

---

## 20. Implementation Plan

Implementation should happen in phases. Do not attempt a single-step port.

### Phase 0: New Repo Bootstrap

Deliverables:

- new repo
- `pyproject.toml`
- lint/test tooling
- package scaffold
- docs scaffold

Exit criteria:

- `uv sync` or equivalent works
- `python -m proceda --help` works

### Phase 1: Data Models and Parser

Deliverables:

- skill models
- session models
- event models
- parser
- local loader

Exit criteria:

- local `SKILL.md` parses
- `proceda lint` works on sample files

### Phase 2: Runtime Core

Deliverables:

- event sink abstraction
- runtime/session abstractions
- adapted executor
- LiteLLM wrapper

Exit criteria:

- skill can execute without CLI UI
- tests cover step transitions and clarifications

### Phase 3: MCP Integration

Deliverables:

- MCP clients
- orchestrator
- tool access validation

Exit criteria:

- sample MCP server works end to end

### Phase 4: Human Interface Layer

Deliverables:

- terminal human interface
- test human interface

Exit criteria:

- approvals and clarifications work without TUI

### Phase 5: CLI

Deliverables:

- `run`
- `lint`
- `replay`
- `doctor`

Exit criteria:

- examples run via CLI

### Phase 6: TUI

Deliverables:

- `dev` command
- Textual app
- live event rendering

Exit criteria:

- polished end-to-end local demo

### Phase 7: Replay and Packaging

Deliverables:

- event log
- replay command
- packaging polish
- docs/examples

Exit criteria:

- launch-quality demo

### Phase 8: v2 Durability

Deliverables:

- remote skill loading
- snapshots
- resume

Exit criteria:

- interrupted run can resume safely

---

## 21. Detailed Task Breakdown

This section is deliberately granular. A junior engineer should be able to execute this work item by item.

### 21.1 Bootstrap Tasks

#### Task 1: Create new repository scaffold

Create:

- `pyproject.toml`
- `src/proceda/__init__.py`
- `src/proceda/cli/main.py`
- `tests/`
- `examples/`
- `docs/`

Acceptance criteria:

- package installs in editable mode
- CLI entrypoint exists

#### Task 2: Add tooling

Add:

- formatter
- linter
- pytest
- type checking if desired

Acceptance criteria:

- CI can run lint and tests

### 21.2 Models and Types

#### Task 3: Implement skill models

Create `proceda/skill.py`.

Implement:

- `StepMarker`
- `SkillStep`
- `Skill`

Acceptance criteria:

- model constructors validated by tests
- marker helper properties work

#### Task 4: Implement session models

Create `proceda/session.py`.

Implement:

- `RunStatus`
- `ToolCall`
- `RunMessage`
- `ApprovalRequest`
- `ClarificationRequest`
- `RunSession`
- `RunResult`

Acceptance criteria:

- model methods update activity timestamps correctly
- terminal states are detectable

#### Task 5: Implement event models

Create `proceda/events.py`.

Implement:

- `RunEvent`
- event payload models
- event serialization helpers

Acceptance criteria:

- JSON serialization round-trip works

### 21.3 Skill Parsing

#### Task 6: Port parser logic

Create `proceda/skills/parser.py`.

Port from existing parser and adapt imports.

Acceptance criteria:

- existing example skills parse successfully
- malformed skills raise typed exceptions

#### Task 7: Implement local loader

Create `proceda/skills/loader.py`.

Behavior:

- if path is a directory, load `SKILL.md`
- if path is a file, load that file
- reject missing files clearly

Acceptance criteria:

- loader accepts both path forms

#### Task 8: Implement lint result model

Create `LintIssue` and `LintResult`.

Behavior:

- separate warnings from errors
- include message and location where possible

Acceptance criteria:

- `proceda lint` can print machine-consumable results later if needed

### 21.4 Runtime Core

#### Task 9: Implement event sink protocol

Create:

- `EventSink`
- `CompositeEventSink`
- `NullEventSink`

Acceptance criteria:

- multiple sinks receive the same event in order

#### Task 10: Implement runtime context manager

Port current context management into `proceda/internal/context.py`.

Acceptance criteria:

- token budgeting is tested

#### Task 11: Port executor

Create `proceda/internal/executor.py`.

Adapt current executor to:

- emit `RunEvent`
- call `HumanInterface`
- avoid any WebSocket assumptions

Acceptance criteria:

- executor runs single-step and multi-step skills
- approvals and clarifications pause correctly

#### Task 12: Define run control loop

Create `proceda/runtime.py`.

Implement:

- `Runtime`
- `RunHandle`

Behavior:

- construct session
- connect event sinks
- invoke executor
- return `RunResult`

Acceptance criteria:

- runtime can be used without CLI

### 21.5 LLM Runtime

#### Task 13: Port LiteLLM wrapper

Create `proceda/llm/runtime.py`.

Port:

- model configuration
- API key handling
- retries
- provider compatibility fixes

Acceptance criteria:

- unit tests cover tool-call parsing

#### Task 14: Port control tool definitions

Create `proceda/llm/tool_schemas.py`.

Implement stable schemas for:

- `complete_step`
- `request_clarification`

Acceptance criteria:

- executor receives these automatically

### 21.6 MCP Integration

#### Task 15: Port MCP models

Create `proceda/mcp/models.py`.

Acceptance criteria:

- tool result parsing tests pass

#### Task 16: Port MCP client transports

Create `proceda/mcp/client.py`.

Port:

- stdio client
- HTTP client

Acceptance criteria:

- mock MCP server tests pass

#### Task 17: Port orchestrator

Create `proceda/mcp/orchestrator.py`.

Adapt to runtime event sinks rather than web logging.

Acceptance criteria:

- tool discovery
- tool lookup
- denylist
- allowlist

#### Task 18: Implement tool executor adapter

Create `proceda/internal/tool_executor.py`.

Behavior:

- convert orchestrator results into runtime-friendly data
- emit tool events

Acceptance criteria:

- tool calls surface messages and structured results

### 21.7 Human Interface

#### Task 19: Define `HumanInterface`

Create `proceda/human.py`.

Acceptance criteria:

- protocol is fully async

#### Task 20: Implement terminal human interface

Behavior:

- inline approval prompts
- inline clarification prompts
- inline error recovery prompts

Acceptance criteria:

- works in plain terminal mode

#### Task 21: Implement test/dummy human interfaces

Implement:

- `AutoApproveHumanInterface`
- `ScriptedHumanInterface`

Acceptance criteria:

- executor tests can run deterministically

### 21.8 CLI

#### Task 22: Implement CLI root

Create `proceda/cli/main.py`.

Acceptance criteria:

- `proceda --help` shows all commands

#### Task 23: Implement `lint`

Acceptance criteria:

- returns non-zero on lint errors

#### Task 24: Implement `run`

Behavior:

- load config
- load skill
- create agent
- run with terminal human interface
- print summary

Acceptance criteria:

- end-to-end example works

#### Task 25: Implement `doctor`

Behavior:

- check Python
- check config
- check env vars
- optional MCP connectivity checks

Acceptance criteria:

- actionable output for missing configuration

#### Task 26: Implement `replay`

Behavior:

- locate run log
- stream saved events
- render in order

Acceptance criteria:

- replay works without network

### 21.9 Event Logging

#### Task 27: Implement run directory manager

Create `proceda/store/event_log.py`.

Behavior:

- create run directory
- write metadata
- append events
- close cleanly

Acceptance criteria:

- repeated runs produce separate directories

#### Task 28: Implement artifact writer

Behavior:

- store optional artifacts and HTML resources returned by tools

Acceptance criteria:

- artifacts directory created only when needed

### 21.10 TUI

#### Task 29: Create Textual app shell

Create `proceda/tui/app.py`.

Acceptance criteria:

- app opens with placeholder panels

#### Task 30: Build step list widget

Acceptance criteria:

- current step is highlighted
- completed steps are visibly distinct

#### Task 31: Build message stream widget

Acceptance criteria:

- new messages append correctly

#### Task 32: Build tool activity widget or panel

Acceptance criteria:

- tool calls and completions are visible

#### Task 33: Build approval modal

Acceptance criteria:

- can approve or reject from keyboard

#### Task 34: Build clarification modal

Acceptance criteria:

- supports free text and option selection

#### Task 35: Connect TUI to event stream

Acceptance criteria:

- live runs update the interface continuously

#### Task 36: Implement `dev` command

Acceptance criteria:

- `proceda dev <path>` launches the TUI and runs the skill

### 21.11 Python Public API

#### Task 37: Implement `Agent`

Create `proceda/agent.py`.

Behavior:

- `from_path`
- `run`
- `create_session`

Acceptance criteria:

- high-level example in docs works exactly

#### Task 38: Implement curated `__init__.py`

Export:

- `Agent`
- `Skill`
- `RunSession`
- `RunResult`
- `HumanInterface`

Acceptance criteria:

- import surface is small and documented

### 21.12 Examples and Docs

#### Task 39: Add example skills

At minimum:

- expense processing
- support escalation
- change-management approval flow

Acceptance criteria:

- examples are runnable

#### Task 40: Add example MCP servers

Acceptance criteria:

- examples can be run locally with clear setup instructions

#### Task 41: Write README

README must include:

- what the project is
- why it exists
- 30-second quickstart
- one end-to-end example

Acceptance criteria:

- a new user can reach first success from README only

### 21.13 v2 Tasks

#### Task 42: Implement remote skill fetcher

Create:

- URL validation
- allowlist
- content size checks
- timeout checks

Acceptance criteria:

- only explicitly allowed domains succeed

#### Task 43: Implement snapshot store

Create:

- session serialization
- atomic writes

Acceptance criteria:

- snapshots are written at step boundaries

#### Task 44: Implement resume command

Acceptance criteria:

- user can resume from a valid interrupted run

---

## 22. Testing Plan

### 22.1 Unit Tests

Required areas:

- parser
- event serialization
- session state transitions
- LLM response parsing
- MCP client behavior
- tool allowlist/denylist
- approval and clarification handling

### 22.2 Integration Tests

Required areas:

- run local skill with mock LLM and mock MCP
- replay from event log
- terminal human interface flows

### 22.3 TUI Tests

Required areas:

- step rendering
- message rendering
- approval modal interactions
- clarification modal interactions

### 22.4 Golden Path E2E

Create at least one end-to-end smoke test that:

1. loads a sample skill
2. uses a fake or deterministic LLM backend
3. uses a mock MCP server
4. completes a run
5. verifies the event log exists

### 22.5 v2 Tests

Add:

- remote fetch allowlist enforcement
- snapshot recovery
- safe resume behavior

---

## 23. Release Plan

### 23.1 v1 Release Checklist

- package published
- README finalized
- examples finalized
- launch demo recorded
- docs finalized
- command surface stable
- event schema documented

### 23.2 Post-v1 Priorities

- resume
- remote skills
- stronger replay UI
- more examples

---

## 24. Appendix: Acceptance Criteria

The implementation is acceptable only if all of the following are true.

### 24.1 Runtime Acceptance

- Local skill executes end to end.
- Pre-step approval pauses before risky tool execution.
- Post-step approval pauses before advancing.
- Clarification prompts wait correctly for user input.
- Invalid tools fail clearly.

### 24.2 CLI Acceptance

- `lint`, `run`, `dev`, `replay`, and `doctor` all work.
- Exit codes are stable and meaningful.
- Errors are actionable.

### 24.3 TUI Acceptance

- A user can understand what the agent is doing without reading logs.
- The current step is always visible.
- Human actions are obvious and easy.

### 24.4 Logging Acceptance

- Every run produces an event log.
- Replay renders from the log without re-executing.

### 24.5 Product Acceptance

- The repo reads like a real SDK.
- The package is not visibly shaped like an extracted backend.
- The first-run experience is impressive enough to serve as a launch demo.

---

## Final Technical Recommendation

Treat this extraction as a product rebuild around an existing engine, not as a file move.

That means:

- preserve semantics
- replace delivery mechanisms
- improve names
- narrow the public API
- make runtime events the core primitive

If that discipline is maintained, the new repo will feel like a modern SDK with a clear identity rather than a repackaged service backend.
