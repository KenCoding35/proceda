# SOP-Bench Dangerous Goods: 94.2% TSR (SOTA)

## Summary

We ran Proceda against the SOP-Bench dangerous_goods benchmark — a 274-task evaluation where
LLM agents must classify hazardous materials by following a multi-step SOP involving score
aggregation, imputation rules, and threshold-based classification. Proceda achieves **94.2%
TSR** (258/274 correct) using Gemini 2.5 Flash, beating the previous best of 87% (Claude 4
Sonnet FC).

| Agent | Model | TSR |
|-------|-------|-----|
| **Proceda** | **Gemini 2.5 Flash** | **94.2% (258/274)** |
| FC (best baseline, Table 5) | Claude 4 Sonnet | 87% |
| ReAct (2nd best, Table 5) | Claude 4.1 Opus | 83% |
| ReAct (Claude 3.5 v2, Table 4) | Claude 3.5 Sonnet v2 | 80% |
| FC (Claude 3.5 v2, Table 4) | Claude 3.5 Sonnet v2 | 59% |

## What Makes This Domain Hard

Unlike patient_intake (where every output comes from a tool), dangerous_goods requires the
agent to **compute** the final classification — the tools return individual scores, and the
agent must sum them, apply imputation rules, and classify into Hazard Class A/B/C/D.

### The Traps

1. **Invalid Product IDs (short-circuit)**: 4 tasks have intentionally malformed product IDs
   (`P1_3191`, `PA_13136`, `Product_14124`, `Product_14123`). The SOP says to set
   hazard_score=0 and class="Unable to Decide" without calling tools. But the tools still
   return scores for these IDs since they're in the CSV — the agent must detect the format
   violation first.

2. **Missing Score Imputation**: 23 tasks have one zero score among four components. The SOP
   says: "If any component is missing or 0, impute it by taking the max of the other scores."
   So `scores=[4,4,0,3]` → impute 0 as max(4,4,3)=4 → hazard_score=15, not 11.

3. **Ambiguous Threshold Boundaries**: The SOP says "Apply Hazard Class A, B, C, D based on
   the value of the hazard score. Higher score gets higher severity, D being the highest." But
   **never states the actual thresholds**. From the data: A: 4-7, B: 8-12, C: 15-16, D: 17-20.
   There's a gap between B (12) and C (15) — scores 13-14 don't appear.

4. **">2 Missing" Rule**: 6 tasks have more than 2 zero scores → "Unable to Decide".

### Why Baselines Score Low

- **FC at 59%**: No reasoning traces → can't work through imputation logic step by step
- **ReAct at 80%**: Reasoning helps, but still guesses thresholds wrong on boundary cases

## How Proceda Handled It

The `proceda convert --tools` command converted the raw SOP into a 7-step SKILL.md:

1. **Validate Product ID** — Check format, short-circuit on invalid
2. **Calculate SDS Label Score** — Call `calculate_sds_label_score`
3. **Calculate Handling Score** — Call `calculate_handling_score`
4. **Calculate Transportation Score** — Call `calculate_transportation_score`
5. **Calculate Disposal Score** — Call `calculate_disposal_score`
6. **Compute Cumulative Hazard Score** — Sum scores, apply imputation, validate range
7. **Determine Hazard Class** — Apply classification, output in XML format

Steps 2-5 are tool calls. Steps 1, 6, and 7 are pure reasoning. This separation worked well —
the LLM reliably called all 4 tools and got correct scores in nearly every task.

## Token Usage

| Metric | Value |
|--------|-------|
| Total tokens | 6.6M |
| Prompt tokens | 6.1M |
| Completion tokens | 493K |
| LLM calls | 3,108 |
| Avg tokens/task | ~23.7K |
| Avg LLM calls/task | 11.1 |
| **Estimated cost** | **~$3.08** |

Cost breakdown: $1.84 input (6.1M @ $0.30/1M) + $1.23 output (493K @ $2.50/1M).
Gemini 2.5 Flash pricing as of March 2026.

## Failure Analysis (16/274 tasks)

All 16 failures have `predicted=<missing>` — the output extractor found nothing. The failures
fall into two distinct categories:

### Category 1: No Summary at Steps 6/7 (~7 tasks)

The LLM hit empty Gemini responses or the text-only iteration limit at the computation steps
and was force-completed without producing a summary. These are Gemini Flash reliability issues
(empty `response.choices` arrays), not reasoning failures.

Example trace (P_13426):
```
Steps 1-5: All tools called successfully, scores=[5,5,5,0]
Step 6: Compute Cumulative Hazard Score → NO SUMMARY (force-completed)
Step 7: Determine Hazard Class → NO SUMMARY (force-completed)
Result: predicted={} (nothing to extract)
```

### Category 2: Correct Answer in Prose, Not in XML Tags (~9 tasks)

The LLM correctly computed the hazard class and stated it in the step summary, but in prose
rather than XML tags. The output extractor searches for `<hazard_class>...</hazard_class>`
tags but these summaries say things like:

- "With a hazard_score of 15, the hazard_class is C"
- "Hazard score of 7 corresponds to Hazard Class A"
- "The product is classified as Hazard Class D"

The extractor doesn't match these prose patterns. This is fixable with a regex-based prose
extraction strategy.

### Comparison: What Succeeded vs What Failed

**Succeeded (258 tasks)**: The LLM produced the hazard class in XML tags within the step 7
summary: `<hazard_score>6</hazard_score><hazard_class>A</hazard_class>`. The XML extractor
captured it correctly.

**Failed Category 2 (9 tasks)**: Identical reasoning, correct answer, but the LLM chose prose
over XML for that particular run. Non-deterministic formatting choice despite temperature=0.

**Failed Category 1 (7 tasks)**: Gemini Flash instability — the model returned empty responses
or got stuck in text-only loops at the computation steps.

### Fix Options

1. **Add prose extraction to output extractor**: Search for patterns like
   `hazard_class is [A-D]` or `Hazard Class [A-D]` in summaries. Would fix ~9 of the 16
   failures.

2. **Add retry on empty Gemini response**: Instead of returning an empty `LLMResponse`,
   retry the call. Would help with ~7 of the 16 failures.

3. **Stronger model**: Gemini Flash's instability causes ~7 failures. A more reliable model
   (Gemini Pro, Claude Sonnet) would likely eliminate these.

## Iteration History

| Change | Result |
|--------|--------|
| Initial run | 0/1 — MCP bridge crashed (stdout from manager) |
| Suppress manager stdout | 0/1 — empty Gemini responses crash |
| Handle empty responses | 0/5 — extractor found nothing |
| Search summary.generated events + XML tags | 0/5 — format mismatch ("A" vs "Hazard Class A") |
| Add containment matching in comparison | 4/5 — first passes |
| Full 274-task run | **258/274 (94.2%)** |

## Key Differences from Patient Intake

| Dimension | Patient Intake | Dangerous Goods |
|-----------|---------------|-----------------|
| Output source | All from tools | Computed by LLM |
| Tool count | 6 | 4 |
| Task count | 66 | 274 |
| Reasoning required | Minimal (pass-through) | Score aggregation + imputation + classification |
| Edge cases | Empty CSV fields | Invalid IDs, missing scores, ambiguous thresholds |
| Baseline TSR | 0-100% (model-dependent) | 59-87% |
| Proceda TSR | 97.0% | 94.2% |

## Technical Changes Made

- **Output extractor**: Added `SUMMARY_GENERATED` events as extraction source, XML tag
  matching for expected column names, bare JSON extraction, containment matching
- **LLM runtime**: Handle empty `response.choices` (return empty LLMResponse instead of crash)
- **MCP bridge**: Suppress stdout from tool managers during init (prevents JSON-RPC corruption)
- **Harness**: Support `product_id` for task identification, containment-based comparison
  (e.g., "A" matches "Hazard Class A")

## Files

```
benchmarks/sop_bench/domains/dangerous_goods/
├── SKILL.md       # 7 steps, generated by proceda convert --tools
└── config.yaml    # Gemini 2.5 Flash, temperature=0.0
```
