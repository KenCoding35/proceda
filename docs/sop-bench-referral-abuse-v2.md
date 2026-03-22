# SOP-Bench Referral Abuse Detection v2 ("Hard"): 88.5% TSR

## Summary

We ran Proceda against the SOP-Bench referral_abuse_detection_v2 benchmark — a 200-task
evaluation where LLM agents must detect referral abuse violations using temporal pattern
analysis, historical violation context, and a risk-severity-based enforcement matrix.
Proceda achieves **88.5% TSR** (177/200 correct) using Gemini 3 Flash Preview.

| Metric | Value |
|--------|-------|
| TSR | 88.5% (177/200) |
| ECR | 100.0% (200/200) |
| Best baseline (Table 5) | 98% (Claude 4 Opus FC) |
| Model | gemini-3-flash-preview |
| Total tokens | 8,274,236 (avg 41,165/task) |
| Total cost | $4.59 |

Unlike most other domains, the SOP and CSV ground truth are in 100% agreement on this
domain. All 23 failures are **genuine LLM reasoning errors** on the complex multi-step
scoring calculation.

## What Makes This Domain Hard

This is the "hard" version of referral abuse detection. Compared to v1:

- **5 violation categories** (vs 4 in v1): adds Temporal Fraud Pattern
- **Weighted indicators** (+2 instead of +1) for strong fraud signals
- **Higher thresholds**: Abusive and Misleading need ≥4 (vs ≥3), No Violation needs ≥6 (vs ≥4)
- **4-tier risk severity**: CRITICAL/HIGH/MEDIUM/LOW based on financial impact and history
- **7 possible enforcement actions** (vs 3 in v1): the action depends on both violation type AND risk severity
- **3x token usage**: 41K tokens/task vs 13K for v1, reflecting more complex reasoning

The scoring step (Step 7) requires the LLM to:
1. Compute 5 scores with weighted indicators across ~30 data fields
2. Determine the highest-scoring category above threshold
3. Calculate risk severity from a separate set of financial/historical criteria
4. Look up the enforcement action in a 2D matrix (violation type × risk level)

## Failure Analysis

### Distribution

| Category | Count | % of failures |
|----------|-------|---------------|
| No Violation wins but LLM picks violation | 14 | 60.9% |
| Inconclusive vs No Action confusion | 7 | 30.4% |
| Risk severity miscalculation | 2 | 8.7% |
| **Total failures** | **23** | — |

### Primary Failure Mode: No Violation Not Recognized (14 tasks)

The most common error: No Violation scores ≥6 (the highest category), but the LLM
also notices a violation category meeting its threshold and picks the violation instead.
This is a "highest score" selection error — the LLM needs to compare all scores and
pick the maximum, but tends to fixate on detected violations.

Examples:
- ACC100001: no_viol=6 vs mislead=4 → LLM picks mislead → "Permanent Account Closure" instead of "No Action"
- ACC100056: no_viol=6 vs mislead=4 → same error
- ACC100189: no_viol=6 vs temporal=4 → LLM picks temporal → "Account Closure" instead of "No Action"

This suggests the LLM has a bias toward flagging violations when any violation indicator
is present, even when the "No Violation" score is higher. The SOP explicitly says "choose
the highest score" but the LLM doesn't always follow this when both violation and
non-violation categories qualify.

### Secondary Failure Mode: Inconclusive Confusion (7 tasks)

4 tasks predicted "No Action" when the correct answer is "Inconclusive" (no score meets
any threshold). 3 tasks predicted "Inconclusive" when the correct answer is "No Action"
(No Violation score ≥6). The LLM confuses the distinction between "no evidence of
violation" (No Violation ≥6 → "No Action") and "insufficient evidence" (nothing meets
threshold → "Inconclusive").

### Risk Severity Errors (2 tasks)

2 tasks correctly identified the violation type but miscalculated the risk severity level,
leading to the wrong enforcement action (e.g., "Account Closure" instead of "Temporary
Suspension").

## Comparison with v1

| Metric | v1 ("Easy") | v2 ("Hard") |
|--------|-------------|-------------|
| TSR | 95.5% | 88.5% |
| ECR | 100% | 100% |
| Tools | 3 | 6 |
| Violation categories | 4 | 5 |
| Enforcement actions | 3 | 7 |
| CSV bugs | 9 (4.5%) | 0 |
| Reasoning errors | 0 | 23 (11.5%) |
| Avg tokens/task | 13,449 | 41,165 |
| Total cost | $1.64 | $4.59 |

v1 achieved perfect SOP-following (all failures were CSV bugs). v2 reveals genuine
reasoning limits — the multi-step scoring with weighted indicators, threshold comparison,
and 2D enforcement matrix exceeds what Gemini 3 Flash can reliably compute in a single
step.

## Configuration

- **Model:** `gemini/gemini-3-flash-preview`, temperature=0.0
- **Execution:** Sequential
- **200 tasks**, single output: `final_decision`
- **6 tools:** investigate_account, analyze_traffic_patterns, analyze_temporal_patterns, get_violation_history, get_financial_impact, determine_enforcement_action
- **Input columns:** `account_id` only (per upstream metadata)

## Possible Improvements

The primary failure mode (No Violation not recognized) might improve with:
1. **Stronger model** — Claude 4 Opus achieves 98% on this domain
2. **Explicit score comparison step** — Break Step 7 into sub-steps: compute scores, then compare, then determine risk
3. **Chain-of-thought prompting** — Force the LLM to write out all 5 scores before deciding

## Files

- `benchmarks/sop_bench/domains/referral_abuse_detection_v2/SKILL.md`
- `benchmarks/sop_bench/domains/referral_abuse_detection_v2/config.yaml`
