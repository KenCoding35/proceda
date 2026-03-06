# SkillRunner OSS SDK Product Specification

**Version**: 0.1.0  
**Status**: Draft  
**Last Updated**: 2026-03-05  
**Audience**: Founders, product, engineering, design, developer relations

---

## Executive Summary

SkillRunner OSS is a terminal-first, Python-native SDK and CLI for turning a Standard Operating Procedure (SOP) into a runnable agent with built-in human oversight.

The open-source product is not a hosted workflow app. It is not a LangChain clone. It is not a graph builder. It is a local-first agent runtime that makes the following workflow natural:

1. Write an SOP in `SKILL.md`
2. Attach tools via MCP
3. Run the SOP as an agent from the terminal
4. Review tool activity live
5. Approve or clarify when required
6. Inspect and replay what happened

The paid hosted web app remains the commercial control plane and collaboration surface. The open-source core is the developer entry point and the ecosystem wedge.

The product thesis is simple:

**The best way to build many real agents is not to hand-author chains or graphs. It is to start from a procedure, make the procedure executable, and preserve human control at the right checkpoints.**

---

## 1. Problem Statement

### 1.1 The Market Problem

Most agent frameworks today force developers into one of two bad starting points:

1. **Prompt-first abstractions**
   - The developer writes a system prompt and hopes the runtime behavior is reliable.
   - Human approval, clarification, resumability, and auditing are added later as ad hoc code.

2. **Graph-first abstractions**
   - The developer builds a workflow graph or state machine up front.
   - This works for deterministic pipelines but is awkward for natural-language procedures, judgment calls, and evolving SOPs.

These frameworks are often too low-level for real operational workflows and too abstract for day-to-day developer productivity.

### 1.2 The User Problem

Teams already have procedures:

- incident response runbooks
- customer support escalations
- onboarding checklists
- approvals and compliance workflows
- finance and operations SOPs
- internal research and synthesis playbooks

Today, those procedures live in docs. A human has to read, interpret, execute, copy state between systems, and remember where approval is required.

This causes:

- inconsistent execution
- poor observability
- weak auditability
- tool switching overhead
- fragile human handoffs
- slow iteration on operational automation

### 1.3 Why Existing Agent Frameworks Fall Short

The current mainstream agent tooling landscape has several gaps:

- **Too much ceremony** for simple but real workflows
- **Weak human-in-the-loop support** as a first-class concept
- **Poor terminal experience** for local development
- **Durability and replay** are typically afterthoughts
- **Tool interfaces are fragmented**
- **Procedures are not the source of truth**

SkillRunner OSS should win by fixing those specific problems rather than competing on the number of abstractions.

---

## 2. Product Thesis

### 2.1 Core Thesis

The core open-source primitive is:

**An SOP becomes a durable agent runtime with first-class tool use, clarification, approval, and replay.**

### 2.2 Product Positioning

SkillRunner OSS should be understood as:

- a **modern Python SDK for agent execution**
- a **CLI/TUI for running and debugging agents locally**
- a **procedure-first runtime**
- an **MCP-native agent framework**

It should not be positioned as:

- a no-code workflow product
- a cloud orchestration platform
- a graph editor
- a generic prompt wrapper

### 2.3 Differentiators

The OSS product should stand out on these dimensions:

| Dimension | SkillRunner OSS Position |
|----------|---------------------------|
| Primary abstraction | SOP / Skill |
| Authoring format | Markdown-first |
| HITL support | Native runtime states |
| Tools | MCP first |
| Local UX | Terminal/TUI first |
| Durability | Event-log-first, resume in v2 |
| Web UI | Paid hosted offering, not OSS focus |

---

## 3. Product Principles

These principles are mandatory and should be used to settle design debates.

### 3.1 Procedure First

The canonical source of truth is the skill definition, not a graph DSL and not a pile of Python callbacks.

### 3.2 Human Control Is Native

Approval and clarification are not plugins. They are runtime states with first-class UX and APIs.

### 3.3 Great Local DX Beats Architectural Purity

The first public win condition is a developer running `skillrunner dev ./my-skill` and immediately understanding what is happening.

### 3.4 One Repo, One Package, One Story

The product must feel like a coherent SDK, not an extracted backend.

### 3.5 MCP Is the Tool Boundary

MCP is the preferred mechanism for tools and resources. Any internal abstraction should align with that boundary.

### 3.6 The Terminal Is the Primary Interface

The open-source product should be fully usable without a browser.

### 3.7 Durability Should Grow Incrementally

v1 should prioritize excellent execution and event logging. v2 adds persistent session recovery and remote skill loading.

---

## 4. Target Users

### 4.1 Primary Persona: Agent Builder

An engineer or technical operator who:

- knows Python
- is experimenting with agents
- wants to operationalize an existing SOP quickly
- wants local control and visibility
- does not want to hand-build state graphs

### 4.2 Secondary Persona: Platform Engineer

An engineer who:

- wants to embed the runtime into internal services
- cares about deterministic interfaces, logs, and replay
- wants MCP-native integration with existing tools

### 4.3 Tertiary Persona: Operations Author

A technically comfortable operator who:

- can write or edit markdown
- wants to test workflow automation locally
- needs safe approvals and review points

---

## 5. Jobs To Be Done

### 5.1 Core Job

"When I have a documented SOP, I want to turn it into a runnable agent without building a bespoke orchestration system."

### 5.2 Supporting Jobs

- "I want to run a skill locally and watch each step happen."
- "I want the runtime to ask me when it needs clarification."
- "I want to approve risky actions before they happen."
- "I want to inspect which tools were called and why."
- "I want to replay a run when something goes wrong."
- "I want to package a reusable workflow for my team."

---

## 6. Product Scope

### 6.1 v1 Scope

Version 1 is the first public open-source release. It is local-first and terminal-only.

#### In Scope

- Python package installable via `pip`
- CLI command `skillrunner`
- Local `SKILL.md` loading from file or directory
- MCP tools over stdio and HTTP
- LLM execution via LiteLLM-backed runtime
- Human approval and clarification in terminal
- Rich terminal/TUI experience
- Skill parsing and linting
- Local run event logging
- Local replay from event log
- Embeddable Python SDK
- Example skills and polished docs

#### Out of Scope

- browser UI
- multi-user collaboration
- authentication/SSO
- hosted service concerns
- remote skill loading
- persistent resumable sessions
- HTML widget rendering
- enterprise admin controls

### 6.2 v2 Scope

Version 2 expands durability and distribution without changing the v1 product shape.

#### In Scope

- remote skill loading with allowlists
- local persistence of run/session snapshots
- resume interrupted runs
- richer inspection tools
- durable local state store
- stricter security controls for remote skills

#### Explicitly Not Included Yet

- hosted control plane
- cloud sync
- browser UI parity with the paid product

---

## 7. Product Boundary: OSS vs Hosted Service

### 7.1 Open Source Includes

- parser
- runtime
- MCP integration
- CLI/TUI
- local event logging
- local replay
- Python SDK
- examples

### 7.2 Hosted Service Retains

- multi-tenant web UI
- authentication and user management
- team collaboration
- hosted persistence
- enterprise controls
- billing
- deployment infrastructure

### 7.3 Positioning Rule

The OSS product must be complete enough to be useful and exciting on its own. It must not feel artificially crippled. The hosted service should win on collaboration, convenience, governance, and hosting, not on basic runtime competence.

---

## 8. Why Python, Not TypeScript

Python is the correct first-language choice for this product.

### 8.1 Reasons

- The existing extractable runtime already exists in Python.
- Most agent developers and LLM practitioners are Python-native.
- The CLI/TUI and local runtime story are strong in Python.
- Shipping a polished Python product now is worth more than delaying for cross-language parity.

### 8.2 Decision

**v1 and v2 are Python-first.**

TypeScript is a future possibility only if:

- there is strong community pull
- the event model and runtime semantics have stabilized
- the Python product is already successful

---

## 9. High-Level User Experience

### 9.1 First-Run Experience

The first successful user journey should feel like this:

```bash
pip install skillrunner
export ANTHROPIC_API_KEY=...
skillrunner run ./examples/expense-processing
```

The user should immediately see:

- the skill title
- steps and current progress
- model/tool activity
- clear prompts for approval or clarification
- a final summary

### 9.2 Ideal Demo Flow

The ideal demo for the README and launch should be:

1. Show a `SKILL.md`
2. Run `skillrunner dev ./skill`
3. Watch the agent move step by step
4. See a tool call
5. Approve a risky action
6. Finish with a run summary

This demo is more important than secondary features.

---

## 10. Core Functional Requirements

### 10.1 Skill Authoring Requirements

**FR-001** The product must accept a `SKILL.md` file or a directory containing `SKILL.md`.

**FR-002** The skill format must remain markdown-first with YAML frontmatter.

**FR-003** The parser must support:

- skill `name`
- skill `description`
- `required_tools`
- `### Step N: Title` headings
- step markers such as `[APPROVAL REQUIRED]`, `[PRE-APPROVAL REQUIRED]`, `[OPTIONAL]`

**FR-004** The parser must reject malformed skills with clear error messages and line-oriented guidance where feasible.

### 10.2 Runtime Requirements

**FR-005** The runtime must execute one step at a time.

**FR-006** The runtime must support LLM-generated tool calls and text responses.

**FR-007** The runtime must support control tools:

- `complete_step`
- `request_clarification`

**FR-008** The runtime must detect and handle:

- repeated text-only non-progress responses
- excessive tool call loops
- invalid tool calls
- denied tool access

**FR-009** The runtime must maintain an explicit session state with at least:

- current step
- completed steps
- status
- message history
- pending approval
- pending clarification
- pending error

### 10.3 Human-in-the-Loop Requirements

**FR-010** A step marked `[PRE-APPROVAL REQUIRED]` must pause before executing app tools for that step.

**FR-011** A step marked `[APPROVAL REQUIRED]` must pause after the step is completed and before advancing.

**FR-012** The user must be able to approve, reject, clarify, retry, skip, or cancel using terminal UX.

**FR-013** Approval and clarification must be visible and auditable in the run log.

### 10.4 Tooling Requirements

**FR-014** Tools must be resolved through MCP.

**FR-015** Both stdio and HTTP MCP servers must be supported.

**FR-016** Tool access must be deny-by-default at the skill level when `required_tools` is declared.

**FR-017** A configurable global tool denylist must exist.

### 10.5 CLI Requirements

**FR-018** The CLI must provide at least:

- `run`
- `dev`
- `lint`
- `replay`
- `doctor`

**FR-019** The CLI must return meaningful exit codes.

**FR-020** The CLI must produce clean plain-text output in non-interactive mode.

### 10.6 TUI Requirements

**FR-021** The dev mode experience must use a full-screen terminal UI.

**FR-022** The TUI must show:

- skill title
- step list
- current step
- live message stream
- tool activity
- approval/clarification prompts
- status footer

**FR-023** The TUI must be fully navigable from the keyboard.

### 10.7 Logging and Replay Requirements

**FR-024** Each run must write a local append-only event log.

**FR-025** The user must be able to replay a previous run from the event log.

**FR-026** Replay must not require access to the original LLM or tool services.

### 10.8 Python SDK Requirements

**FR-027** The product must expose a simple high-level Python API for loading and running skills.

**FR-028** The product must expose a lower-level event-driven API for embedding.

**FR-029** The product must allow custom human interfaces and custom event consumers.

---

## 11. Non-Functional Requirements

**NFR-001** The package must install cleanly on Python 3.11+.

**NFR-002** The default developer workflow must work on macOS and Linux. Windows support is desirable but not required for v1.

**NFR-003** The CLI must feel responsive and readable under normal local development conditions.

**NFR-004** Errors must be actionable and specific.

**NFR-005** Sensitive values should be redacted in logs by default.

**NFR-006** The package must be usable offline except for LLM and MCP endpoints.

**NFR-007** The codebase must be structured so the hosted web app can later consume the same runtime/event model.

---

## 12. Command Surface

The initial command surface should be intentionally small and polished.

### 12.1 `skillrunner run`

Run a skill in standard interactive mode.

```bash
skillrunner run ./skills/expense-processing
skillrunner run ./skills/expense-processing --model anthropic/claude-sonnet-4-20250514
skillrunner run ./skills/expense-processing --var ticket_id=INC-123
```

Requirements:

- Accept a file path or directory path
- Use terminal prompts for approvals and clarifications
- Print final summary
- Exit non-zero on failure or rejection

### 12.2 `skillrunner dev`

Run a skill in full-screen TUI mode.

```bash
skillrunner dev ./skills/expense-processing
```

Requirements:

- Show steps and progress
- Show reasoning when enabled
- Show tool calls/results live
- Allow approval/clarification inline

### 12.3 `skillrunner lint`

Validate a skill statically.

```bash
skillrunner lint ./skills/expense-processing
```

Requirements:

- Parse the skill
- Validate markers and step structure
- Validate required tool names against configured MCP tools when possible
- Surface warnings and errors separately

### 12.4 `skillrunner replay`

Replay a historical run from local event logs.

```bash
skillrunner replay .skillrunner/runs/20260305_101522_abcd1234
skillrunner replay <run-id>
```

Requirements:

- Render prior run events without re-executing tools or LLM calls
- Work even if upstream services are unavailable

### 12.5 `skillrunner doctor`

Validate local environment and configuration.

```bash
skillrunner doctor
```

Requirements:

- Check Python version
- Check config file presence
- Check LLM API key availability
- Check MCP connectivity where possible
- Print actionable remediation steps

### 12.6 Deferred Commands

These should not ship in v1 unless the implementation is nearly free:

- `skillrunner resume`
- `skillrunner fetch`
- `skillrunner auth`
- `skillrunner serve`

---

## 13. TUI Requirements

### 13.1 Layout

The full-screen TUI should have three main regions:

- **Left pane**: skill metadata and step list
- **Main pane**: messages, tool activity, prompts
- **Footer/header**: status, model, shortcuts, current mode

### 13.2 Required Visual States

- idle / preparing
- running
- awaiting approval
- awaiting clarification
- failed
- completed

### 13.3 Required Interaction Model

The TUI must support:

- arrow-key navigation when relevant
- enter to confirm
- single-key shortcuts for approve/reject when safe
- escape to dismiss non-destructive overlays
- a help shortcut

### 13.4 Dev Mode Details

Dev mode should surface:

- tool call payloads
- tool results
- reasoning blocks if enabled
- raw event stream or event details pane if feasible

The purpose of dev mode is to make debugging unusually good, not to mimic the paid web UI.

---

## 14. Skill Format

### 14.1 Canonical Format

The open-source product continues to use `SKILL.md`.

Example:

```markdown
---
name: expense-processing
description: Process expense reports with policy validation and approval checkpoints
required_tools:
  - receipts__extract
  - policy__validate
  - erp__submit
---

### Step 1: Extract receipt data
Use the receipts tool to extract all available receipt fields.

### Step 2: Validate policy
[APPROVAL REQUIRED]
Check the extracted data against company policy and summarize any violations.

### Step 3: Submit to ERP
[PRE-APPROVAL REQUIRED]
Submit the approved expense report to the ERP system.
```

### 14.2 Authoring Rules

- Frontmatter `name` and `description` are required.
- Steps must use `### Step N: Title`.
- Marker text must appear inside the step body.
- `required_tools` is strongly recommended for all non-trivial skills.

### 14.3 Design Decision

The OSS project intentionally stays markdown-first because:

- it keeps authoring lightweight
- it matches how SOPs are already written
- it avoids prematurely inventing a DSL

---

## 15. Configuration

### 15.1 Local Config File

The default config filename should be:

```text
skillrunner.yaml
```

The CLI may also support `--config <path>`.

### 15.2 Config Scope

Config must support:

- LLM configuration
- MCP app definitions
- skill search paths
- logging settings
- denylist settings
- dev mode settings

### 15.3 Example

```yaml
llm:
  model: anthropic/claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY
  temperature: 0.7
  max_tokens: 4096

apps:
  - name: receipts
    description: Receipt extraction tools
    transport: stdio
    command: ["python", "-m", "receipts_server"]

  - name: policy
    description: Expense policy validation
    transport: http
    url: http://localhost:8001/mcp

dev:
  show_reasoning: true
  log_mcp: true

security:
  tool_denylist:
    - dangerous__*
```

---

## 16. Session Lifecycle

The runtime must expose explicit lifecycle states.

### 16.1 States

- `created`
- `running`
- `awaiting_approval`
- `awaiting_input`
- `suspended` (reserved for v2 persistence/resume)
- `completed`
- `failed`
- `cancelled`

### 16.2 State Rules

- A run begins in `created`.
- `start` moves it to `running`.
- Approval requests move it to `awaiting_approval`.
- Clarification requests move it to `awaiting_input`.
- Completion, failure, and cancellation are terminal.

---

## 17. v2 Product Additions

Version 2 should extend the product without changing the core developer mental model.

### 17.1 Remote Skill Loading

Allow:

```bash
skillrunner run https://raw.githubusercontent.com/org/repo/main/skill/SKILL.md
```

Requirements:

- explicit allowlist
- HTTPS by default
- content size limit
- timeout limit
- optional local cache

### 17.2 Persistence and Resume

Allow:

```bash
skillrunner resume <run-id>
```

Requirements:

- session snapshots at safe checkpoints
- consistent event log
- recovery of pending approval/clarification state
- clear user messaging on restarts

---

## 18. Success Metrics

### 18.1 Product Metrics

These metrics are directional, not hard launch gates:

- time from install to first successful run under 10 minutes
- time from existing SOP to working skill under 30 minutes for a technical user
- strong README-to-run conversion
- strong GitHub save/star/share behavior

### 18.2 Experience Metrics

- users can understand a live run without reading source code
- human checkpoints are obvious and trustworthy
- failures are diagnosable from logs and replay

---

## 19. Launch Criteria for v1

v1 is ready when all of the following are true:

1. A user can install the package and run a local example skill end to end.
2. Approval and clarification flows work cleanly in terminal mode.
3. The TUI feels intentional and polished.
4. `lint`, `run`, `dev`, `replay`, and `doctor` all work.
5. Example MCP integrations are available.
6. The README demo works exactly as advertised.
7. Event logs are stable enough to support replay.

---

## 20. Product Risks

### 20.1 Risk: It Feels Like an Internal Extraction

Mitigation:

- restructure the repo around the SDK, not around the old backend
- invest in naming, docs, examples, and terminal UX

### 20.2 Risk: Terminal-Only Feels Limiting

Mitigation:

- make the terminal UX excellent
- keep browser UI clearly positioned as the paid product

### 20.3 Risk: Markdown Skills Feel Too Loose

Mitigation:

- provide linting
- provide examples
- provide strong conventions
- keep the parser strict where it matters

### 20.4 Risk: Tool Integrations Are Too Hard

Mitigation:

- lean into MCP
- include sample MCP servers
- provide `doctor` output and debugging tools

---

## 21. Open Questions

These questions should be resolved before implementation freeze, but they should not block repo bootstrapping:

1. Should the public package and CLI be named `skillrunner`, or should the OSS project adopt a new standalone brand?
2. Should `skillrunner init` exist in v1, or can examples and docs cover initial skill authoring?
3. Should replay be text-only in v1, or should it reuse the full TUI?

Current recommendation:

- keep package name `skillrunner` for the first extraction
- defer `init`
- implement replay in the TUI if feasible, otherwise plain rich output is acceptable for v1

---

## 22. Final Product Statement

The open-source SkillRunner SDK should be:

- obviously useful on day one
- beautiful in the terminal
- procedural rather than graph-theoretic
- human-controlled by default
- easy to embed
- easy to explain

If the product ships in that shape, it will not just be "the open-source version of the backend." It will be a compelling contribution to the agent tooling landscape on its own terms.
