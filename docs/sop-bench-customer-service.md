# SOP-Bench Customer Service: 30.1% TSR (vs 79% Baseline)

## Summary

Proceda achieves **30.1% TSR** (47/156) with **100% ECR** on the customer_service domain.
This is below the 79% baseline (Llama 3.3 70B ReAct). The domain exposes limitations in both
the output extraction pipeline and Gemini Flash's reasoning on complex branching SOPs.

| Agent | Model | TSR |
|-------|-------|-----|
| ReAct (best baseline, Table 5) | Llama 3.3 70B | 79% |
| FC (2nd best, Table 5) | Claude 4.5 Sonnet | 71% |
| **Proceda** | **Gemini 2.5 Flash** | **30.1% (47/156)** |
| FC (Claude 3.5 v2, Table 4) | Claude 3.5 Sonnet v2 | 14% |
| ReAct (Claude 3.5 v2, Table 4) | Claude 3.5 Sonnet v2 | 3% |

## Why This Domain Is Hard

Customer service has the most complex branching logic in SOP-Bench:

- 10 tools, 11 steps (most of any domain we've run)
- 4 possible outcomes: RESOLVED, PENDING_ACTION, ESCALATED, FAILED
- Heavy branching: invalid account → FAILED, terminated account → FAILED, outage detected →
  PENDING_ACTION, troubleshooting works → RESOLVED, troubleshooting fails → ESCALATED
- Many tools return JSON with nested data structures and NaN values
- The SOP has conditional steps (5, 6, 10 are OPTIONAL) that depend on account status

## Failure Analysis (109/156 tasks failed)

### Category 1: Missing Predictions — 44 tasks (40% of failures)

The output extractor found no parseable `final_resolution_status`. The LLM produced the answer
in its step 11 summary but in prose that didn't match any extraction pattern. These are
extraction/formatting failures, not reasoning failures.

### Category 2: False "ACTIVE" Extractions — 23 tasks (21%)

The prose extractor matched "account status is Active" or "status is ACTIVE" from earlier
step summaries instead of the final resolution status. The extractor takes the last match
for the `status` suffix, but account status mentions appear throughout the workflow.

### Category 3: RESOLVED vs ESCALATED Confusion — 16 tasks (15%)

The LLM concluded RESOLVED when it should have concluded ESCALATED. This is a genuine
reasoning error — the LLM looked at diagnostic results and decided the issue was fixed when
the SOP's logic would have required escalation (e.g., metrics didn't improve enough).

### Category 4: Other Reasoning Errors — 26 tasks (24%)

Various mismatches including PENDING_ACTION vs FAILED, text fragments being extracted as
values, and edge cases in the branching logic.

## What Proceda Did Right

- **100% ECR** — All 156 tasks completed, no crashes (including handling NaN values in tool results)
- **Correct tool ordering** — The 11-step structure correctly sequenced all 10 tools
- **Conditional step handling** — Optional steps (5, 6, 10) were correctly skipped when the
  account was Active and not Suspended
- **Tool call success** — When tools were called, parameters were correct

## What Needs Improvement

1. **Output extraction** — The prose extractor needs domain-awareness or a more structured
   approach. The step 11 summary should instruct the LLM to output in a specific format.

2. **Stronger model** — Gemini 2.5 Flash struggles with the complex branching logic (4 outcomes,
   6+ branch points). The baselines use Llama 3.3 70B and Claude 4.5 Sonnet — significantly
   more capable models for reasoning.

3. **Converter quality** — The SOP converter could generate more explicit instructions for
   Step 11 about outputting the `final_resolution_status` in a parseable format (e.g., XML
   tags or JSON).

## Token Usage

| Metric | Value |
|--------|-------|
| Total tasks | 156 |
| Avg time per task | ~24s |
| Total run time | ~63 minutes |

## Technical Changes Made

- **MCP bridge**: Added NaN/Inf sanitization for JSON serialization (customer_service tools
  return NaN values in diagnostic timestamps)
- **Prose extractor**: Added last-match preference and column name suffix matching
- **Harness**: Generalized task ID detection for account_id

## Key Takeaway

Customer service represents a qualitative shift from earlier domains. Patient intake and
dangerous goods are primarily about **execution** (call the right tools in the right order
with the right parameters). Customer service is about **reasoning** (interpret branching
conditions, decide which outcome applies based on accumulated evidence). Proceda's structured
execution helps with the first part but the LLM reasoning quality bottleneck becomes dominant.

The 30.1% TSR vs 79% baseline gap is largely explained by:
1. Model quality (Gemini Flash vs Llama 70B/Claude Sonnet)
2. Output extraction (44 missing predictions = 28% of tasks)
3. Prose extractor false positives (23 ACTIVE extractions = 15%)

Fixing items 2 and 3 alone would likely bring TSR to ~60-70%.
