# Bug Report: referral_abuse_detection_v1 CSV labels follow a closure-priority rule that contradicts the SOP

## TL;DR

9 of 200 tasks in the `referral_abuse_detection_v1` CSV have `enforcement_action = "Account Closure"` despite a higher-scoring non-closure category meeting its threshold. The SOP explicitly says "choose the highest score" (line 108), but the labeled dataset exactly matches an alternate rule: if Abusive Account Creation or Misleading Ad Copy clears its threshold, output "Account Closure" regardless of other scores.

Separately, the SOP's tiebreaker rule (line 110) omits No Violation from the priority order, creating ambiguity for 2 additional tasks where Misleading Ad Copy and No Violation tie.

## Summary

The SOP's scoring logic (section 5.5.1, lines 69-117) defines four violation categories, each with a threshold. When multiple categories meet their thresholds, the SOP states:

> **Line 107-108:** STEP 2: Determine violation type based on HIGHEST score
> - If multiple scores >= threshold, choose the highest

> **Line 110:** - If tied scores → Use priority order: Abusive Account Creation > Misleading Ad Copy > Personal Orders

The tiebreaker only applies when scores are **tied**. When one category scores strictly higher than another, the higher score should win regardless of which maps to a more severe action.

In all 9 affected tasks, Misleading Ad Copy scores exactly 3 (minimum threshold), while Personal Orders or No Violation scores 4 (strictly higher). Per the SOP, the higher-scoring category should win. But the CSV assigns "Account Closure" (the Misleading Ad Copy action) instead of "No Action" (the Personal Orders / No Violation action).

**Impact:** Recomputing labels from the repo-local CSV and SOP scoring rules yields 191/200 agreement. The 9 disagreements are exactly the 9 tasks listed below. A strict SOP-following agent will score at most 191/200 (95.5%) on this domain, since `enforcement_action` is the expected output (`metadata.json`, line 3) and the evaluator compares agent output directly against that label (`evaluation/evaluator.py`, line 332).

## Affected Files

All paths relative to the repository root.

- `src/amazon_sop_bench/benchmarks/data/referral_abuse_detection_v1/sop.txt` — Lines 107-110 (scoring rules)
- `src/amazon_sop_bench/benchmarks/data/referral_abuse_detection_v1/test_set_with_outputs.csv` — CSV lines 42, 43, 45, 46, 53, 73, 77, 175, 189 (task IDs 40, 41, 43, 44, 51, 71, 75, 173, 187)

## Issue 1: Labels generated under a different rule than the SOP (9 tasks)

### The SOP Scoring Rules

**File:** `src/amazon_sop_bench/benchmarks/data/referral_abuse_detection_v1/sop.txt`

The SOP defines four scoring categories (lines 76-105):

**Abusive Account Creation** (threshold ≥ 3, lines 76-82):
- address_validity is false (+1)
- email_pattern_suspicious is true (+1)
- website_verified is false (+1)
- connected_accounts >= 15 (+1)
- login_geographic_consistency is false (+1)

**Misleading Ad Copy** (threshold ≥ 3, lines 84-89):
- website_verified is false (+1)
- referral_source_quality is "Low" or "Medium" (+1)
- order_patterns_suspicious is true (+1)
- click_through_rate > 0.4 (+1)

**Personal Orders** (threshold ≥ 3, lines 91-96):
- payment_method_shared is true (+1)
- connected_accounts > 0 AND connected_accounts < 15 (+1)
- order_patterns_suspicious is true (+1)
- referral_source_quality is "High" (+1)

**No Violation** (threshold ≥ 4, lines 98-105):
- address_validity is true (+1)
- email_pattern_suspicious is false (+1)
- website_verified is true (+1)
- login_geographic_consistency is true (+1)
- payment_method_shared is false (+1)
- order_patterns_suspicious is false (+1)

The enforcement action mapping (lines 112-117):
- Abusive Account Creation → "Account Closure"
- Misleading Ad Copy → "Account Closure"
- Personal Orders (Related) → "No Action"
- No Violation → "No Action"
- INCONCLUSIVE → "Inconclusive"

### The 9 Mislabeled Tasks

In every case, Misleading Ad Copy scores exactly 3 (minimum threshold). But another category scores strictly higher (4). The SOP says to choose the highest — so the higher-scoring category should determine the enforcement action.

| CSV Line | Task ID | Account | Abuse | Mislead | Personal | No Viol | SOP Winner (highest) | SOP Action | CSV Action |
|----------|---------|---------|-------|---------|----------|---------|---------------------|------------|------------|
| 42 | 40 | ACC100040 | 1 | **3** | 3 | **4** | No Violation (4) | No Action | Account Closure |
| 43 | 41 | ACC100041 | 3 | **3** | **4** | 1 | Personal (4) | No Action | Account Closure |
| 45 | 43 | ACC100043 | 3 | **3** | **4** | 1 | Personal (4) | No Action | Account Closure |
| 46 | 44 | ACC100044 | 1 | **3** | **4** | 3 | Personal (4) | No Action | Account Closure |
| 53 | 51 | ACC100051 | 1 | **3** | **4** | 3 | Personal (4) | No Action | Account Closure |
| 73 | 71 | ACC100071 | 1 | **3** | **4** | 3 | Personal (4) | No Action | Account Closure |
| 77 | 75 | ACC100075 | 1 | **3** | 3 | **4** | No Violation (4) | No Action | Account Closure |
| 175 | 173 | ACC100173 | 1 | **3** | **4** | 3 | Personal (4) | No Action | Account Closure |
| 189 | 187 | ACC100187 | 2 | **3** | **4** | 2 | Personal (4) | No Action | Account Closure |

### Worked Example: ACC100040 (CSV Line 42, Task ID 40)

CSV data for this account:

```
address_validity=True, email_pattern_suspicious=False, website_verified=False,
connected_accounts=1, login_geographic_consistency=True,
referral_source_quality=High, payment_method_shared=False,
order_patterns_suspicious=True, click_through_rate=1.98
```

Score calculation:
- **Abuse**: (not True) + False + (not False) + (1≥15=False) + (not True) = 0+0+1+0+0 = **1** (below threshold 3)
- **Mislead**: (not False) + ("High" in Low/Med = False) + True + (1.98>0.4=True) = 1+0+1+1 = **3** (meets threshold 3)
- **Personal**: False + (0<1<15=True) + True + ("High"=True) = 0+1+1+1 = **3** (meets threshold 3)
- **No Viol**: True + (not False) + False + True + (not False) + (not True) = 1+1+0+1+1+0 = **4** (meets threshold 4)

Three categories meet their thresholds: Mislead (3), Personal (3), No Violation (4).

Per the SOP (line 108): "choose the highest" → No Violation at score 4 wins → enforcement action = **"No Action"**.

The CSV says **"Account Closure"** — which would only be correct if Misleading Ad Copy (score 3) were chosen over No Violation (score 4).

### Root Cause

This is not 9 isolated bad labels. The entire labeled dataset is perfectly consistent with an alternate rule: *if Abusive Account Creation or Misleading Ad Copy clears its threshold, output "Account Closure"; otherwise if Personal Orders or No Violation clears its threshold, output "No Action."* This closure-priority rule produces exactly the same labels as the CSV for all 200 tasks. It disagrees with the SOP's explicit "choose the highest score" instruction on the 9 tasks where a non-closure category scores strictly higher than a closure category.

## Issue 2: SOP tiebreaker omits No Violation (2 tasks)

The SOP's tiebreaker rule (line 110) specifies priority for tied scores:

> If tied scores → Use priority order: Abusive Account Creation > Misleading Ad Copy > Personal Orders

**No Violation is not listed.** This creates ambiguity when Misleading Ad Copy and No Violation tie at the same score. Two tasks hit this case:

| CSV Line | Task ID | Account | Mislead | No Viol | CSV Action |
|----------|---------|---------|---------|---------|------------|
| 132 | 130 | ACC100130 | 4 | 4 | Account Closure |
| 181 | 179 | ACC100179 | 4 | 4 | Account Closure |

Both have Misleading Ad Copy and No Violation tied at 4, with no other category meeting its threshold. The CSV resolves both as "Account Closure" (Misleading Ad Copy), but the SOP does not define how to break this tie.

This is a separate issue from Issue 1: these 2 tasks are currently counted as correct for a closure-priority agent, but only because the tiebreaker ambiguity happens to align with closure priority. A strict SOP-following agent has no basis to choose either way.

## Verification

Computing the SOP's scoring rules programmatically across all 200 tasks produces exactly 191 agreements and 9 disagreements — the same 9 CSV lines listed above. No other tasks are affected (the 2 tie-ambiguity tasks happen to agree with both the SOP-priority and closure-priority interpretations).

## Suggested Fix

1. **Fix the 9 labels:** Update CSV lines 42, 43, 45, 46, 53, 73, 77, 175, 189 in `test_set_with_outputs.csv` to set `enforcement_action = "No Action"`, matching the SOP's "choose the highest score" rule.

2. **Fix the tiebreaker:** Add No Violation to the SOP's priority order at line 110, e.g.: "If tied scores → Use priority order: Abusive Account Creation > Misleading Ad Copy > Personal Orders > No Violation."

3. **Add a regression test:** A test that recomputes expected enforcement actions from the SOP's stated scoring rules and verifies they match the CSV labels would prevent this class of issue.
