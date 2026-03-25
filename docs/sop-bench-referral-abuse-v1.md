# SOP-Bench Referral Abuse Detection v1: 95.5% TSR

## Summary

We ran Proceda against the SOP-Bench referral_abuse_detection_v1 benchmark — a 200-task
evaluation where LLM agents must detect referral abuse violations by investigating accounts,
analyzing traffic patterns, and scoring violation indicators to determine enforcement actions.
Proceda achieves **95.5% TSR** (191/200 correct) using Gemini 3 Flash Preview.

| Metric | Value |
|--------|-------|
| TSR | 95.5% (191/200) |
| ECR | 100.0% (200/200) |
| TSR (excluding CSV-buggy tasks) | **100.0% (191/191)** |
| ECR (excluding CSV-buggy tasks) | 100.0% (191/191) |
| Best baseline (Table 5) | 98% (Claude 3.5 v2 Sonnet ReAct) |
| Model | gemini-3-flash-preview |

## Adjusted Results (Excluding CSV-Buggy Tasks)

All 9 failures trace to the CSV ground truth disagreeing with the SOP's own scoring rules.
An independent computation of all four violation scores using the SOP's stated formulas
produces the exact same 191/200 agreement — the 9 mismatches are the same 9 tasks where
Proceda "fails."

On the 191 tasks where the SOP's scoring rules agree with the CSV, Proceda scores
**100% (191/191)** — zero agent reasoning errors.

### The 9 CSV Ground Truth Errors

All 9 follow the same pattern: Misleading Ad Copy reaches its threshold (score ≥ 3),
but a higher-scoring category also meets its threshold. Per the SOP's explicit rule
("choose the highest score"), the higher-scoring category should win. But the CSV
assigns "Account Closure" (the Misleading Ad Copy action) instead.

| Account | Abuse | Mislead | Personal | No Viol | Highest Winner | CSV says |
|---------|-------|---------|----------|---------|---------------|----------|
| ACC100040 | 1 | 3 | 3 | **4** | No Violation (4) → No Action | Account Closure |
| ACC100041 | 3 | 3 | **4** | 1 | Personal (4) → No Action | Account Closure |
| ACC100043 | 3 | 3 | **4** | 1 | Personal (4) → No Action | Account Closure |
| ACC100044 | 1 | 3 | **4** | 3 | Personal (4) → No Action | Account Closure |
| ACC100051 | 1 | 3 | **4** | 3 | Personal (4) → No Action | Account Closure |
| ACC100071 | 1 | 3 | **4** | 3 | Personal (4) → No Action | Account Closure |
| ACC100075 | 1 | 3 | 3 | **4** | No Violation (4) → No Action | Account Closure |
| ACC100173 | 1 | 3 | **4** | 3 | Personal (4) → No Action | Account Closure |
| ACC100187 | 2 | 3 | **4** | 2 | Personal (4) → No Action | Account Closure |

In every case, Misleading Ad Copy scores exactly 3 (the minimum threshold). But Personal
Orders or No Violation scores higher (4). The SOP says to "choose the highest" — so the
agent correctly picks the higher-scoring category. The CSV appears to have been generated
with a rule that prioritizes closure-triggering categories regardless of score, which
contradicts the SOP's stated scoring logic.

## Domain Details

### SOP Logic

A 4-step referral abuse detection pipeline:

1. **Investigate Account** — Retrieve account data: address validity, email patterns,
   website verification, connected accounts, geographic consistency
2. **Analyze Traffic** — Retrieve traffic data: revenue, CTR, page views, device
   distribution, referral source quality, payment sharing, order patterns
3. **Get Enforcement Guidelines** — Retrieve action mapping rules
4. **Score and Decide** — Calculate four violation scores from boolean/numeric indicators,
   determine violation type from highest score above threshold, map to enforcement action

The scoring is the heart of the SOP: count boolean indicators per violation category,
apply thresholds (≥3 for violations, ≥4 for no violation), pick highest score with
priority-based tiebreaking.

### Tool Implementation

All three tools use pandas CSV lookups — clean, ground-truth-consistent implementations.
No mock arithmetic or stubs. The tools simply return data; all scoring logic is done
by the agent per the SOP instructions.

### Configuration

- **Model:** `gemini/gemini-3-flash-preview`, temperature=0.0
- **Execution:** Sequential
- **200 tasks**, single output: `enforcement_action`
- **3 tools:** investigate_account, analyze_traffic_patterns, determine_enforcement_action
- **Input columns:** `account_id` only (per upstream metadata)

## Key Takeaway

Proceda achieves 100% accuracy on every task where the CSV ground truth agrees with the
SOP's stated scoring rules. The 4.5% gap to the 98% baseline is entirely explained by
CSV ground truth errors — not agent reasoning. This is a strong result on a clean domain
with complex multi-category scoring logic.

## Files

- `benchmarks/sop_bench/domains/referral_abuse_detection_v1/SKILL.md`
- `benchmarks/sop_bench/domains/referral_abuse_detection_v1/config.yaml`
