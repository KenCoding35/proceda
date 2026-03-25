# SOP-Bench Traffic Spoofing Detection: 79.5% TSR

## Summary

We ran Proceda against the SOP-Bench traffic_spoofing_detection benchmark — a 200-task
evaluation where LLM agents must detect affiliate marketing traffic spoofing violations by
validating partner accounts, analyzing traffic patterns, authenticating sources, and
determining enforcement actions. Proceda achieves **79.5% TSR** (159/200 correct) using
Gemini 3 Flash Preview.

| Metric | Value |
|--------|-------|
| TSR | 79.5% (159/200) |
| ECR | 100.0% (200/200) |
| TSR (excluding SOP/CSV-buggy tasks) | **98.8% (159/161)** |
| Best baseline (Table 5) | 86% (Claude 4.1 Sonnet ReAct) |
| Model | gemini-3-flash-preview |

## Adjusted Results (Excluding SOP/CSV-Buggy Tasks)

39 of the 41 failures trace to the CSV ground truth contradicting the SOP's explicit rules.
On the 161 tasks where the SOP and CSV agree, Proceda scores **98.8% (159/161)** — only 2
genuine agent reasoning errors.

### The SOP/CSV Disagreement (39 tasks)

The SOP (section 5.6) defines this enforcement mapping:

| Risk Level | Enforcement Action |
|-----------|-------------------|
| High | Account Closure |
| Medium | Temporary Suspension |
| Low (with evidence) | Warning Issued |
| Low (no evidence) | No Action |

The CSV has **39 tasks with `risk_level=Medium` but `enforcement_action=Warning Issued`**.
The SOP never prescribes "Warning Issued" for Medium risk — that action is explicitly for
Low risk only. An agent faithfully following the SOP will answer "Temporary Suspension" for
all Medium-risk tasks and get these 39 wrong.

There is **no distinguishing signal** between the two Medium subgroups:
- Both have `traffic_analysis_result=SUSPICIOUS` and `source_verification_result=WARNING`
- No tool returns any differentiating information
- All numeric inputs (engagement score, bounce rate, etc.) overlap completely
- The split appears arbitrary — there is no rule an agent could learn

All 39 failures follow the exact same pattern:
- **Predicted:** Temporary Suspension (matches SOP for Medium risk)
- **Expected:** Warning Issued (contradicts SOP for Medium risk)

### Enforcement Action Distribution in CSV

| Risk Level | Enforcement Action | Count |
|-----------|-------------------|-------|
| High | Account Closure | 92 |
| Medium | Temporary Suspension | 50 |
| Medium | Warning Issued | 39 (bug) |
| Low | No Action | 19 |

## The 2 Genuine Failures

Only 2 failures are actual agent reasoning errors:

| Task | Predicted | Expected | Risk Level | Violation Type | Issue |
|------|-----------|----------|------------|---------------|-------|
| PARTNER193 | Warning Issued | No Action | Low | None | Agent saw evidence_collected and inferred a warning was needed |
| PARTNER251 | Warning Issued | No Action | Low | None | Same — agent misread evidence presence as requiring a warning |

Both tasks have `violation_type=NaN` (no violation identified) and `evidence_collected` with
actual values (screenshots, URLs, etc.). The SOP says "Low risk without conclusive evidence →
No Action." The correct interpretation is that `violation_type=None` means no actionable
violation was found, so "No Action" regardless of what evidence was collected. The agent
incorrectly interpreted the presence of evidence as triggering the "Low risk with evidence →
Warning Issued" path.

All 17 other Low-risk tasks have the same pattern (`violation_type=NaN`, `enforcement_action=
No Action`) and the agent gets them correct — these 2 are edge cases where the LLM's
interpretation wavered.

## Domain Characteristics

- **6 tools**: InvestigateViolations → AnalyzeTrafficPatterns → ValidateReferralSources →
  CalculateRiskScore → GenerateEvidenceReport → ExecuteEnforcementAction
- **Single output field**: `enforcement_action` (4 possible values)
- **Tool quality**: All tools are clean CSV lookups — no random values, no hardcoded
  computation. GenerateEvidenceReport returns "SUCCESS" and ExecuteEnforcementAction returns
  a fixed confirmation string (neither provides the enforcement action).
- **Pipeline**: Linear 6-step pipeline, each step maps to exactly one tool call
- **Key insight**: The enforcement action must be determined by the agent from `risk_level`
  (returned by CalculateRiskScore) and the SOP rules — no tool directly returns it.

## Comparison with Baselines

The best baseline from the paper (Table 5) is **86% TSR** (Claude 4.1 Sonnet ReAct). However,
baseline agents also face the same SOP/CSV disagreement on the 39 Medium→Warning Issued tasks.
Baseline agents may achieve higher raw TSR if they happen to not follow the SOP strictly on
those tasks — but this would reflect less faithful SOP execution, not better reasoning.

On the 161 tasks where the SOP is unambiguous, Proceda's 98.8% demonstrates near-perfect
SOP execution.

## Cost and Performance

- **Execution time**: ~12s per task (2,400s total, ~40 min)
- **LLM calls per task**: ~8 (6 tool calls + overhead)
- **Model**: gemini-3-flash-preview, temperature=0.0
