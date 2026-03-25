# How Proceda Was Designed and Built: A Process Report

*The design back-and-forth between a solo founder and Claude Code that produced a SOTA SOP-execution engine.*

---

## Origin: SkillRunner (January 2026)

Proceda did not begin as Proceda. It began as **SkillRunner** — a full-stack web application (FastAPI + React) for turning enterprise SOPs into executable workflows with LLM reasoning and human oversight.

The first commit landed on **January 16, 2026**. Vivek Haldar, recently departed from a VP of Engineering role, was bootstrapping an AI startup as a solo founder. The thesis: enterprise organizations maintain vast SOP libraries as static documents — what if those documents could execute themselves?

The initial product vision was a two-pane web UI: skill definition on the left, execution chat on the right, with inline app UIs rendered via MCP. The LLM would step through an SOP written in markdown, calling tools and pausing for human approval at marked checkpoints.

By January 22, a working prototype existed: skill parser, config system, HTTP API, WebSocket coordination, LLM runtime (LiteLLM), MCP clients, session management, and a React frontend.

## The Design Critique Loop

What makes the SkillRunner design process distinctive is the structured critique loop. Rather than designing in isolation and implementing, Vivek ran the product spec through **three rounds of staff-engineer-level design critiques** with Claude Code, each escalating in severity and specificity.

### Critique Round 1: Structural Gaps

The first critique identified critical issues that would have caused production failures:

- **State ownership contradiction.** The design simultaneously claimed "state in LLM context" as canonical (Section 3.5) while keeping authoritative state in the backend SessionManager (Sections 5.4, 6.1). These are mutually exclusive — if the LLM context drifts, which source of truth wins?

- **Approval handling was underspecified.** The `[APPROVAL REQUIRED]` marker only triggered post-step approval. But post-step means the LLM has already called tools — including potentially irreversible ones (delete, submit, pay).

- **Path traversal vulnerability.** The skill loading API accepted user-specified paths with no normalization, a classic local file read risk.

- **No tool access control.** All discovered MCP tools were available to all skills. The critique called this "a security and policy risk for enterprise."

### Critique Round 2: Security and Correctness

The second round escalated several issues to blockers:

- **Pre-step approval was missing.** The critique explicitly stated: "Post-step approval only is unsafe for irreversible actions. You need pre-step approval markers or a 'preflight' approval mode." This directly led to the `[PRE-APPROVAL REQUIRED]` marker in the final design — a feature that became architecturally load-bearing for production SOPs.

- **Persistence scope was internally inconsistent.** Section 2.2 declared "Non-Goal: persistent state across sessions," but Section 5.4 and Phase 6 assumed a SessionStore exists. The critique demanded a decision.

- **iFrame sandbox was weaker than claimed.** The `srcDoc` + `allow-scripts` approach enabled XSS. Nonce validation on postMessage offered no protection because injected scripts could read the nonce from the HTML.

- **Context budget was hand-wavy.** The design acknowledged the problem ("future summarization") but offered no concrete strategy. The critique warned: "For long skills, this will blow the context budget."

### Critique Round 3: Schema Mismatches

The third round caught implementation-level gaps that would have caused runtime errors:

- **Missing Session fields.** The Executor referenced `pending_clarification` and `pre_approval_granted` — fields that did not exist in the Session model.

- **Tool allowlist defaults were dangerous.** Section 8.6 defaulted to "all tools if `required_tools` is absent." The critique called this unsafe for enterprise.

- **Skill parser brittleness.** The `### Step N` regex would misparse real-world SOPs with non-standard headings, nested headings, or tables.

### What the Critiques Changed

The critique loop's impact is visible in the implemented code. The code review conducted in February 2026 (grading the SkillRunner codebase at B+) specifically praised design elements that trace directly to critique feedback:

- **Deny-by-default tool access.** Skills must explicitly declare `required_tools` in frontmatter. If absent, no app tools are available. The global denylist overrides skill-level allowlists. The code review called this "genuinely strong."

- **Layered error recovery.** Categorized errors with `recoverable`, `user_message`, and `details` metadata. Error recovery flow wired through the full stack. The code review called the error system (~950 lines) "unusually well-structured."

- **MCP subprocess lifecycle.** Proper escalation on cleanup: close stdin → wait(2s) → terminate → wait(1s) → kill.

- **Context trimming.** Token counting with tiktoken for OpenAI/Claude, character-based fallback for other providers. History truncation preserves critical messages (approval records, step boundaries, clarification exchanges).

Some critiqued issues remained partially resolved. The state ownership question was addressed pragmatically (backend session state wins, LLM context is managed) rather than architecturally. The iFrame security concern (CSP with `unsafe-inline` is cosmetic) was acknowledged but deferred, with the trade-off logged. The approval pre/post ambiguity was resolved in implementation but never formally updated in the design doc.

## The Pivot: Extracting Proceda (March 5, 2026)

By early March, SkillRunner was a working product: 1,330+ backend tests, 544+ frontend tests, deployed to staging and production on Cloud Run. But a strategic question emerged: **the execution kernel was too valuable to be trapped inside a web application.**

The SkillRunner execution engine — skill parser, LLM runtime, executor, MCP integration, event system — could operate independently of the web UI. Three observations drove the extraction:

1. **SDK vs. web app.** The runtime should be embeddable as a Python library, not just consumed via WebSocket from a browser.

2. **Open source potential.** The core engine could be a standalone open-source project, separate from the commercial hosting platform. The OSS product must be complete and exciting on its own — not artificially crippled.

3. **Terminal-first use case.** Local development, scripting, benchmarking, and CLI usage needed a runtime that worked without a browser.

On March 5, 2026, the Proceda repository was seeded with product spec and technical design documents. Within two days, two competing implementations were produced:

- **Implementation A:** Core runtime, CLI, and tests.
- **Implementation B:** Full v1 with CLI, TUI, runtime, MCP, and 172 tests.

A detailed comparative analysis (`67ec104`) evaluated both. Implementation B won — it was more complete, better tested, and closer to the vision.

### Key Architectural Decisions in the Extraction

The extraction was not a copy-paste. Several deliberate design pivots were made:

**Event stream over WebSocket coordination.** SkillRunner used WebSocket + REST for frontend coordination. Proceda replaced this with in-process event streams. The rationale: "CLI and TUI need local event subscriptions, not socket transport. Events are a better primitive for replay, embedding, and later web adapters."

**Terminal-only v1.** No HTML widget rendering. Browser UI is part of the hosted value proposition (SkillRunner's commercial moat). Terminal focus is strategically cleaner for open source.

**Event log in v1, session resume in v2.** Full resume requires tight snapshot semantics. Event replay — valuable for debugging, demos, and benchmarking — was achievable in v1. This scope cut kept the initial release tractable.

**Preserve SKILL.md format.** The critique rounds had questioned the markdown parser's brittleness, but the format was already implemented, understood, and matched the product thesis (procedure-first, not graph-first). The extraction reaffirmed it.

**One package, not many.** A single `proceda` package rather than splitting into `proceda-core`, `proceda-mcp`, etc. Stronger product story, lower cognitive overhead. The alternative (internal package sprawl) was explicitly rejected.

The package was initially named `skillrunner`, then renamed to `proceda` on the same day (`21df683`).

## The Boomerang: Proceda Back Into SkillRunner (March 9–16)

Once Proceda was stabilized as an independent SDK, SkillRunner adopted it as its core engine dependency. This was executed in 10 phases over a week:

- **Phases 0–1:** Add Proceda as path dependency. Replace skill models and parser with Proceda's versions. Delete SkillRunner's copies. Migrate from 0-based to 1-based step indices.
- **Phase 2:** Replace SessionStatus enum with Proceda's RunStatus.
- **Phase 3:** Replace LLM runtime with Proceda's utilities (thinking tag parsing, tool result formatting).
- **Phase 4:** Keep MCP client in SkillRunner — Proceda's version lacked UI resource extraction features needed for the web frontend.
- **Phases 5–7:** Replace context manager and summary generator. Build an event bridge to translate Proceda RunEvents into SkillRunner ExecutionEvents.
- **Phases 8–9:** Update remaining modules. Fix frontend step indices (0-based → 1-based).
- **Phase 10:** Full test suite verification — 1,361 backend + 544 frontend tests passing.

The result: SkillRunner became a thin web hosting layer over Proceda's execution engine. Proceda owns the runtime. SkillRunner owns the multi-tenant web experience.

## The Working Style: Solo Founder + Claude Code

The development pattern visible in the commit history reveals a distinctive working style:

### Design-first, then implement

Every major feature started with a design document or product spec, not code. The SOP converter had a design doc (`12fbcc0`) before a line of implementation. The Proceda extraction had a full technical design with extraction maps and implementation phases. Even the SOP-Bench benchmark run had a status document that was updated continuously.

### Structured critique as quality gate

Rather than reviewing code after the fact, the design critique loop front-loaded quality. Three rounds of critique on the product spec caught state ownership contradictions, security gaps, and schema mismatches before they became bugs. This is unusual for a solo founder project — most solo projects skip design review entirely.

### Competing implementations with comparative analysis

For the Proceda extraction, two complete implementations were produced and evaluated side-by-side. The analysis (`67ec104`) examined code quality, test coverage, architectural alignment, and completeness before picking a winner. This is a deliberate strategy: let the AI produce multiple approaches, then evaluate rather than iterate on one.

### Rapid iteration with continuous documentation

The git history shows documentation commits interspersed with code commits, not batched at the end. Design docs were updated as decisions changed. CLAUDE.md (the AI collaborator guide) was maintained as a living document, updated when new patterns emerged.

### Claude Code as staff engineer, not code monkey

The critique loop, comparative analysis, and code review suggest Claude Code was used as a design partner rather than a typing accelerator. The design critiques read like genuine staff-engineer reviews — they identify contradictions, escalate severity, demand decisions, and sometimes disagree with the proposed approach. The code review grades the codebase (B+) and identifies specific bugs (litellm race condition, session state mutation) alongside architectural strengths.

## Timeline Summary

| Date | Milestone |
|------|-----------|
| Jan 16, 2026 | SkillRunner MVP begins — product spec, initial implementation |
| Jan 16–22 | Design critique rounds 1–3 shape architecture |
| Jan 22 – Feb 11 | Full-stack implementation across 42 tasks |
| Feb 11–19 | Production features: auto-save, Cloud Run deployment, PDF converter |
| Feb 26 | Code review: B+ grade, 1,330+ tests, security and concurrency issues flagged |
| Mar 5 | Proceda repo seeded — extraction begins |
| Mar 5–6 | Two competing implementations; Implementation B wins with 172 tests |
| Mar 5 | Package renamed from `skillrunner` to `proceda` |
| Mar 6–9 | Hardening: pre-commit hooks, docs, bug fixes, OSS prep |
| Mar 8–9 | Open-source release: license, packaging, README |
| Mar 9 | SOP converter feature added (LLM-based SKILL.md generation) |
| Mar 9–16 | SkillRunner adopts Proceda as engine (10-phase migration) |
| Mar 10–15 | `output_fields` feature — Customer Service jumps from 30% to 81% TSR |
| Mar 15–24 | SOP-Bench benchmark: 10 domains run, SOTA on 4, 6 benchmark bugs found |
| Mar 23–24 | Design analysis and results reports published |

## Unresolved Tensions

Several design debates from the critique rounds remain partially resolved:

**State ownership.** The backend session state is authoritative in practice, but full session resume (pause at step 3, close everything, resume days later) remains a v2 feature.

**Approval semantics.** Pre-step and post-step approval markers both exist and work, but the design never formally specified which to use when. In practice, `[PRE-APPROVAL REQUIRED]` is for irreversible actions and `[APPROVAL REQUIRED]` is for review-after-execution. This heuristic is not documented.

**iFrame security.** CSP with `unsafe-inline` is acknowledged as cosmetic for the SkillRunner web frontend. The threat model (are MCP apps trusted first-party or untrusted third-party?) was debated but never formally decided.

**Skill parser brittleness.** The `### Step N` format works for machine-generated SKILL.md files (via the converter) but struggles with hand-authored SOPs that use non-standard heading formats. The converter partially solves this by normalizing input, but the parser itself remains strict.

## What the Process Produced

From a standing start on January 16 to SOTA benchmark results on March 24 — roughly 10 weeks — the process produced:

- **SkillRunner:** A production-deployed multi-tenant web application with 1,361+ backend tests and 544+ frontend tests.
- **Proceda:** An open-source Python SDK with 172+ tests, published on PyPI, achieving state-of-the-art on SOP-Bench with Gemini Flash models.
- **6 benchmark bug reports** filed against SOP-Bench itself.
- **Three companion articles:** benchmark results report, 48-hour journey narrative, and architectural design analysis.

The design critique loop, competing implementations, and structured extraction demonstrate that a solo founder with Claude Code can produce work that would typically require a small team — provided the process front-loads design quality rather than treating it as an afterthought.
