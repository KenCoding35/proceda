# SOP-Bench Aircraft Inspection: 98.2% TSR

## Summary

We ran Proceda against the SOP-Bench aircraft_inspection benchmark — a 112-task evaluation
where LLM agents must conduct pre-flight airworthiness verification by calling 7 inspection
tools in sequence and recording their results. Proceda achieves **98.2% TSR** (110/112 correct)
using Gemini 2.5 Flash via OpenRouter.

| Agent | Model | TSR |
|-------|-------|-----|
| **Proceda** | **Gemini 2.5 Flash (OpenRouter)** | **98.2% (110/112)** |
| FC (best baseline, Table 5) | Claude 4.1 Opus | 99% |
| ReAct (2nd best, Table 5) | Claude 4.1 Opus | 99% |

## What Makes This Domain Work Well

Aircraft inspection is a pure tool-calling domain: every output column comes directly from a
tool result. The 7-step SOP maps cleanly to 7 sequential tool calls, each producing one output
field. There's no computation, imputation, or judgment required — the agent calls the tool with
the right arguments and records the result.

### The 7 Output Columns

| Step | Tool | Output Field |
|------|------|-------------|
| 1 | VerifyAircraftClearance | aircraft_ready |
| 2 | VerifyMechanicalComponents | mechanical_inspection_result |
| 3 | VerifyElectricalSystems | electrical_inspection_result |
| 4 | ReportComponentIncident | component_incident_response |
| 5 | ReportComponentMismatch | component_mismatch_response |
| 6 | CrossCheckSpecifications | cross_check_response |
| 7 | ReportCrossCheck | cross_check_reporting_response |

Steps 4-7 use outputs from earlier steps as inputs (e.g., Step 4 passes
`mechanical_inspection_result` and `electrical_inspection_result` from Steps 2-3). The agent
must carry forward results across steps.

## Failure Analysis (2/112 tasks)

Both failures (task_42 and task_49) have the exact same root cause and failure mode.

### Root Cause: Empty Gemini Responses at Step 7

Both tasks complete Steps 1-6 correctly — all 6 tools are called with correct arguments, all
6 output fields match expected values. At Step 7 ("Report Cross-Check Results"), Gemini
returns empty responses (0 completion tokens) repeatedly:

```
Step 7 trace (both tasks):
  LLM call → 0 completion tokens (empty response)
  LLM call → 0 completion tokens (empty response)
  LLM call → 0 completion tokens (empty response)
  ...repeated ~6 times...
  Hit text-only iteration limit
  "You seem to be stuck" nudge messages loop
  Step force-completed without tool call
```

The model never calls `ReportCrossCheck`, so `cross_check_reporting_response` is never
produced. The predicted output has 6/7 fields correct but is missing the 7th.

### What the Tasks Have in Common

Both are "everything fails" tasks:
- `aircraft_ready: false`
- `mechanical_inspection_result: fail`
- `electrical_inspection_result: fail`
- `component_incident_response: failed`
- `component_mismatch_response: failed`
- `cross_check_response: failed`
- Expected `cross_check_reporting_response: failed`

It's possible the combination of all-failing results in the context causes Gemini Flash to
produce empty responses at the final step. The 110 successful tasks include many with partial
and full failures, so this is likely a non-deterministic Gemini reliability issue rather than
a systematic pattern.

### Fix Options

1. **Retry on empty response**: The executor already handles empty Gemini responses, but
   the retry budget gets exhausted at the text-only iteration limit. A targeted retry on
   zero-completion-token responses before counting against the iteration limit would help.

2. **Stronger model**: The baselines achieve 99% with Claude 4.1 Opus. A more reliable
   model would likely eliminate these empty-response failures.

## Configuration

### Model: Gemini 2.5 Flash via OpenRouter

This was the first domain run through OpenRouter rather than direct Gemini API. The
`config.yaml` uses `openrouter/google/gemini-2.5-flash` with `OPENROUTER_API_KEY`.

### Code Changes Required

This domain required three code changes to handle Gemini's tool name normalization behavior:

1. **Normalized tool name matching in orchestrator** (`src/proceda/mcp/orchestrator.py`):
   Gemini snake_cases PascalCase tool names (e.g., `VerifyAircraftClearance` becomes
   `verify_aircraft_clearance`). Added `_normalize_tool_name()` that strips separators
   and lowercases for fuzzy matching. `resolve_tool()` now tries normalized matching
   after exact matching fails. The `_check_required_tool()` method also uses normalized
   comparison.

2. **Resolve before access check** (`src/proceda/mcp/orchestrator.py`): `call_tool()`
   now resolves the tool name first, then checks access on the resolved qualified name.
   Previously it checked access on the raw (possibly unresolved) name, which would fail
   for normalized names.

3. **Thinking config passthrough** (`src/proceda/config.py`, `src/proceda/llm/runtime.py`):
   Added `thinking` field to `LLMConfig` and pass it to litellm as `{"type": thinking_value}`
   when set. Not used for this domain's run but needed for future thinking-model support.

## Files

```
benchmarks/sop_bench/domains/aircraft_inspection/
├── SKILL.md       # 7 steps, 7 tools, 7 output fields
└── config.yaml    # Gemini 2.5 Flash via OpenRouter, temperature=0.0
```
