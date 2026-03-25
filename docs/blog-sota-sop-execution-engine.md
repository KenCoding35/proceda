# Anatomy of a SOTA Agentic SOP-Execution Engine

*A design analysis of Proceda's architecture and how structured execution enables state-of-the-art on SOP-Bench with models that cost a fraction of the baselines.*

---

There is a phrase gaining traction in the AI engineering community: **harness engineering**. Prompt engineering concerned itself with crafting the right input to an LLM. Harness engineering concerns itself with crafting the right *execution environment* around it — shifting emphasis from "what you say to the model" to "what you let the model do, when, and how you constrain it."

[Proceda](https://github.com/vivekhaldar/proceda), run against Amazon's [SOP-Bench](https://arxiv.org/abs/2506.08119) — a benchmark with 2,411 tasks across 14 business domains — achieved state-of-the-art on 4 of 10 runnable domains, with 8 of 10 on SOP-consistent tasks. The models used were Gemini 2.5 Flash and Gemini 3 Flash. The baselines they beat were Claude 4 Opus, Claude 4.1 Opus, and Claude 4 Sonnet.

The performance gap stems from the execution harness, not the underlying model.

This post is a technical design analysis of *how*. It is a companion to the [results report](sop-bench-results.md) (which covers the numbers) and the [48-hour journey post](blog-sop-bench-journey.md) (which covers the story). This piece covers the architecture.

## The Thesis

The claim is narrow and specific: **for procedural tasks, a well-designed execution harness substitutes for raw model capability.**

Procedural tasks have defined steps, tool dependencies, and deterministic outcomes — *Patient Intake*, *KYC compliance*, *Dangerous Goods* classification, *Content Moderation*, *Order Fulfillment*. These are not open-ended reasoning problems. They are procedures: sequences of steps with tool calls, decision gates, and branching logic that must be executed faithfully.

SOP-Bench tests exactly this. Each domain provides a multi-step Standard Operating Procedure, a set of mock tools, and ground truth labels. The question: can an AI agent follow the procedure, call the right tools, and produce the correct output?

The baselines in the SOP-Bench paper use two standard agent architectures:

- **Function Calling (FC):** The full SOP is placed in the system prompt alongside all tool schemas. The model determines the sequence autonomously.
- **ReAct:** The same setup, augmented with a thought-action-observation loop.

Both treat the SOP as prompt context. Proceda treats it as a state machine.

## How Baselines and Proceda Differ

```
FC / ReAct (baseline approach):
┌─────────────────────────────┐
│         System Prompt       │
│  ┌───────────────────────┐  │
│  │  Full SOP (30 steps)  │  │
│  │  All tool schemas     │  │
│  │  Task variables       │  │
│  └───────────────────────┘  │
│                             │
│  LLM reasons about entire  │
│  procedure in one context  │
└──────────────┬──────────────┘
               │
         Tool calls
               │
         Final answer

Proceda (structured execution):
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│    Step 1         │     │    Step 2         │     │    Step N         │
│  Instructions     │────▶│  Instructions     │────▶│  Instructions     │
│  Tool schemas     │     │  Tool schemas     │     │  + output_fields  │
│  ↓                │     │  ↓                │     │  ↓                │
│  LLM calls tools  │     │  LLM calls tools  │     │  LLM calls tools  │
│  ↓                │     │  ↓                │     │  ↓                │
│  complete_step()  │     │  complete_step()  │     │  complete_step()  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
       Executor advances ──────────────────────────────▶
```

This represents a category difference, not a degree difference. The baseline architectures require the model to function as both planner and executor. Proceda separates those concerns: the SOP defines the plan, the harness manages the execution lifecycle, and the model handles one step at a time.

## Seven Design Decisions That Enable Cheaper-Model SOTA

Each decision below is connected to a specific benchmark outcome. The pattern is consistent: the harness absorbs complexity that would otherwise fall on the model.

### 1. The SOP as State Machine

A SKILL.md file is parsed into a sequence of `SkillStep` objects. The executor walks through them with a simple loop:

```
while current_step <= total_steps:
    prompt LLM with step instructions
    run LLM loop until complete_step() is called
    handle approval gates if needed
    advance to next step
```

The model never receives a prompt like "you are on step 3 of 12, here is what you did in steps 1 and 2, now figure out what to do next." Instead, it receives: "Execute Step 3: Validate insurance. Here are the instructions. Here are the tools. Call `complete_step` when done."

**Evidence: *Patient Intake*.** This domain requires a strict 6-tool dependency chain where the final tool needs outputs from all 5 previous tools. Both baseline architectures score 0% with Claude 3.5 Sonnet v2 — the model cannot manage the sequencing. The paper shows that Claude 4.1 Opus (the most expensive model in the comparison) is required to reach 100%. Proceda reaches 97% with Gemini 2.5 Flash by decomposing the chain into 6 steps, each with one tool call.

**Principle: Reduce the reasoning surface per LLM call.** Rather than asking the model to plan, provide a plan and ask it to execute one piece.

### 2. Control Tools as Explicit Progress Signals

Two "control tools" are always injected into every LLM call alongside the domain's actual tools:

- `complete_step(summary)` — the LLM signals that the current step is done
- `request_clarification(question, options)` — the LLM asks the human for input

The model *must* call `complete_step` to advance. There is no implicit step detection — no pattern matching on the model's text output to infer completion. The model makes an explicit, structured declaration.

This prevents the model from silently skipping steps, rambling past step boundaries, or confusing "thinking about the step" with "completing the step."

The harness includes a two-tier fallback for models that produce text without calling tools:

1. **Soft nudge** (every N text-only responses): "You seem stuck. Call `complete_step` if done, or use a tool to make progress."
2. **Hard cap** (5x the nudge threshold): Force-complete the step and move on.

**Evidence: 100% Execution Completion Rate.** Across all 10 domains, every single task ran to completion. No crashes, no infinite loops, no stalls. The nudge/force-complete mechanism catches any model that loses track, without failing the entire run.

**Principle: Make progress legible.** State transitions should be required as structured actions, not inferred from prose.

### 3. Context Trimming (The Forgetting Strategy)

The context manager applies aggressive token budgeting:

1. Always preserve system messages (the skill definition)
2. Always preserve "critical" messages (step prompts, clarification responses)
3. Fill remaining token budget with recent non-critical messages, newest first
4. If anything was trimmed, insert a notice

The step prompt for the current step is marked as critical at creation time, so it is never trimmed. Old tool results from previous steps are the first to go.

**Evidence: *Dangerous Goods*.** This domain has 274 tasks, many requiring multiple tool calls per step across a multi-step procedure. Without trimming, later steps would have their context window dominated by tool results from earlier steps — results the model no longer needs. The trimming ensures the model always has the current step's instructions and recent tool results in view.

**Principle: Context is a resource to be managed, not accumulated.** The right information at the right time outperforms all information all the time. A 1M token window becomes unnecessary when the harness keeps the active window focused.

### 4. Structural Approval Gates

SKILL.md supports two approval markers:

- `[APPROVAL REQUIRED]` — human reviews after step completion, before advancing
- `[PRE-APPROVAL REQUIRED]` — human must approve before step execution begins

These are parsed from the markdown by the parser (regex-based marker extraction) and enforced by the executor's step loop. The LLM never decides whether to pause for approval. The harness makes that decision based on the SOP's structural markers.

**Evidence:** This did not directly affect benchmark scores (SOP-Bench runs with auto-approve). However, it is load-bearing for the design philosophy: every decision removed from the model is a decision it cannot get wrong.

For production SOPs — the actual use case Proceda is built for — this is table stakes. More broadly, it illustrates the principle of separating policy from execution.

**Principle: Policy enforcement belongs in the harness, not the model.**

### 5. output_fields and Structured Extraction

The SKILL.md frontmatter can declare output fields:

```yaml
output_fields:
  - final_resolution_status
  - escalation_required
```

When present, the system prompt instructs the model to emit XML tags in its final `complete_step` summary:

```
<final_resolution_status>RESOLVED</final_resolution_status>
<escalation_required>NO</escalation_required>
```

The extractor then parses these deterministically — no fuzzy matching, no regex on prose, no ambiguity between "RESOLVED" and "the status should be resolved."

**Evidence: *Customer Service* — 30.1% to 81.4%.** Before `output_fields`, the model was producing correct answers but expressing them in free-form prose. The output extractor would match "account status is ACTIVE" (from a tool result) instead of "final resolution status is RESOLVED" (the agent's actual answer). The model had the answer; the harness could not extract it.

This was the single most impactful change in the entire benchmark run. A 51-point improvement from changing how the model formats its output — with no change to how it reasons.

**Principle: Structure the interface between model output and downstream systems.** Deterministic extraction of structured output, rather than parsing prose, costs zero model capability and delivers massive gains.

### 6. Guard Rails as Circuit Breakers

The executor enforces hard limits on every step:

| Guard Rail | Threshold | What Happens |
|-----------|-----------|-------------|
| Text-only responses (soft) | Every 5 | Nudge: "call complete_step or use a tool" |
| Text-only responses (hard) | 15 | Force-complete the step |
| Total iterations per step | 50 | Raise execution error |
| App tool calls per step | 20 | Trigger error recovery (retry/skip/cancel) |

The tool call circuit breaker merits attention. If a step exceeds 20 app tool calls, execution does not crash — it pauses and asks the human (or auto-approve in benchmarks) whether to retry (reset the counter), skip the step, or cancel the run.

**Evidence: 100% ECR again.** These limits are generous — 50 iterations is substantial, and most steps complete in 2–5. But they are finite. Unbounded loops are the enemy of reliability, and the cost of a slightly-too-early force-complete is far lower than the cost of a runaway token spend or infinite loop.

**Principle: Bounded execution is a feature, not a limitation.**

### 7. Event-Driven Observability

Every runtime transition emits a structured event: step started, tool called, tool completed, LLM usage, approval requested, status changed, and 20+ other types. These are written to a JSONL trace file for every task.

This may appear to be a nice-to-have. In practice, it was the mechanism that made every other improvement possible.

- The `output_fields` breakthrough came from trace analysis. The traces showed 100% ECR but 30% TSR on *Customer Service* — and revealed exactly where extraction was failing: the model's answer was in the `complete_step` summary, but the extractor was picking up a field from an earlier tool result.
- The benchmark bug discoveries came from traces. When Proceda follows the SOP correctly but scores wrong, the trace proves it. This is how the analysis revealed that *Traffic Spoofing*'s CSV labels contradict its SOP for 39 tasks.
- The thinking model analysis came from traces. The traces revealed the model spending tokens on extended reasoning about straightforward arithmetic — reasoning that provided no benefit and sometimes introduced errors.

**Principle: Instrument everything.** Improvement requires observation. Traces are the foundation of eval-driven development — the feedback loop that makes systematic improvement possible.

## The Thinking Model Paradox

The most counterintuitive result from the benchmark run was the model comparison on *Referral Abuse v2*:

| Model | Type | TSR |
|-------|------|-----|
| Gemini 2.5 Pro | Thinking (extended reasoning) | 74.5% |
| Gemini 3 Flash | Non-thinking, cheap | 88.5% |
| Gemini 3.1 Pro | Non-thinking, mid-tier | 99.0% (SOTA) |

The thinking model — the one that spends extra compute on chain-of-thought reasoning — performed worst. The cheap non-thinking model beat it by 14 points.

The explanation: *Referral Abuse* requires calculating penalty scores from a table, comparing them, and selecting the right violation. The procedure is arithmetic and table lookups, fully specified by the SOP. The thinking model treated each task as a reasoning puzzle, sometimes second-guessing the SOP's instructions or over-analyzing edge cases that were not edges.

This represents the clearest evidence for the structured execution thesis. Thinking models allocate compute to *reasoning about what to do*. When the harness already provides that structure — the SOP is the plan, the step prompt is the instruction, the tool schemas define the interface — additional reasoning about planning becomes wasted compute. Worse, it can introduce errors through over-analysis of straightforward decisions.

Thinking models solve a different problem: they help when the task requires figuring out *what* to do. Structured SOP execution already specifies what to do. The model need only execute.

## The Cost Curve Inversion

| Domain | Proceda Model | Proceda TSR | Baseline Model | Baseline TSR |
|--------|--------------|-------------|----------------|-------------|
| *Dangerous Goods* | Gemini 2.5 Flash | **94.2%** | Claude 4 Sonnet | 87% |
| *Customer Service* | Gemini 2.5 Flash | **81.4%** | Llama 3.3 70B | 79% |
| *Aircraft Inspection* | Gemini 2.5 Flash | **100%** | Claude 3.7 Sonnet | 99% |
| *Patient Intake* | Gemini 2.5 Flash | **97.0%** | Claude 4.1 Opus | 100% |
| *Referral Abuse v2* | Gemini 3.1 Pro | **99.0%** | Claude 4 Opus | 98% |

Gemini 2.5 Flash is roughly an order of magnitude cheaper per token than Claude 4 Opus. On *Dangerous Goods*, the cheaper model wins by 7.2 percentage points. On *Aircraft Inspection*, it ties (100% vs 99%). On *Patient Intake*, it trails by 3 points — but the baseline required Claude 4.1 Opus, the most expensive model in the comparison.

The pattern suggests a boundary. For domains with **deterministic decision logic** — even complex multi-step logic like *Dangerous Goods* classification — cheap models with structured execution match or beat expensive models with unstructured execution.

For domains requiring **subjective judgment** — like *Know Your Business*, where the SOP says to escalate on risk indicators but the ground truth follows unstated rules — stronger models retain an advantage. Proceda scored 42.2% on *Know Your Business* with Gemini 3.1 Pro, versus 58% for the Claude 4.5 Opus ReAct baseline.

---

*Proceda is open source at [github.com/vivekhaldar/proceda](https://github.com/vivekhaldar/proceda). Full benchmark results are in the [SOP-Bench results report](sop-bench-results.md). The 48-hour benchmarking journey is in [How We Achieved SOTA on SOP-Bench in 48 Hours](blog-sop-bench-journey.md). Built by [Enchiridion Labs](https://enchiridionlabs.online).*
