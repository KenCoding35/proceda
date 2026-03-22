# Bug Report: traffic_spoofing_detection CSV labels assign "Warning Issued" to Medium-risk tasks, contradicting the SOP

## TL;DR

39 of 200 tasks in the `traffic_spoofing_detection` CSV have `risk_level = "Medium"` but
`enforcement_action = "Warning Issued"`. The SOP (section 5.6) explicitly maps Medium risk
to "Temporary Suspension" and reserves "Warning Issued" for Low risk only. Note that
`risk_level` is a direct task input (`metadata.json`, line 4), not something the agent must
infer — the benchmark hands the agent "Medium" up front. We did not find any documented
rule, single-field threshold, or simple combination of available non-identifier signals that
cleanly separates these 39 tasks from the 50 other Medium-risk tasks that correctly map to
"Temporary Suspension." An agent faithfully following the SOP will score at most 161/200
(80.5%).

## Summary

The SOP's enforcement action determination (section 5.6) defines a clear mapping from risk
level to enforcement action:

> **Section 5.6 — Enforcement Action Determination:**
> - High risk violations: Account Closure
> - Medium risk violations: Temporary Suspension
> - Low risk violations with evidence: Warning Issued
> - Low risk violations without conclusive evidence: No Action

The CSV's `enforcement_action` column follows this mapping for High and Low risk tasks, but
splits Medium risk into two actions with no observable distinguishing rule:

| Risk Level | Enforcement Action | Count | SOP-Consistent? |
|-----------|-------------------|-------|-----------------|
| High | Account Closure | 92 | Yes |
| Medium | Temporary Suspension | 50 | Yes |
| Medium | Warning Issued | 39 | **No** — SOP says Temporary Suspension |
| Low | No Action | 19 | Yes |

**Impact:** The SOP never prescribes "Warning Issued" for Medium risk. A strict SOP-following
agent will answer "Temporary Suspension" for all Medium-risk tasks and get 39 wrong. Since
`enforcement_action` is the sole output column (`metadata.json`), this directly caps TSR at
80.5%.

## Affected Files

All paths relative to the repository root.

- `src/amazon_sop_bench/benchmarks/data/traffic_spoofing_detection/sop.txt` — Section 5.6
  (enforcement action mapping)
- `src/amazon_sop_bench/benchmarks/data/traffic_spoofing_detection/test_set_with_outputs.csv`
  — CSV lines 17, 20, 21, 22, 23, 29, 31, 34, 36, 37, 43, 46, 53, 62, 65, 71, 78, 79, 81,
  84, 88, 91, 98, 104, 107, 108, 117, 118, 124, 129, 134, 146, 152, 178, 179, 188, 190,
  197, 198 (39 tasks)

## The 39 Mislabeled Tasks

All 39 share the same pattern:
- `risk_level = "Medium"` (from the CSV's ground truth and from the `CalculateRiskScore` tool)
- `traffic_analysis_result = "SUSPICIOUS"` (from `AnalyzeTrafficPatterns`)
- `source_verification_result = "WARNING"` (from `ValidateReferralSources`)
- `investigation_status = "Completed"` (from `InvestigateViolations`)
- `enforcement_action = "Warning Issued"` in the CSV (contradicts SOP)

The 50 correctly-labeled Medium-risk tasks have the **exact same tool outputs**:
SUSPICIOUS, WARNING, Completed. There is no distinguishing signal.

### Affected Partner IDs

PARTNER115, PARTNER118, PARTNER119, PARTNER120, PARTNER121, PARTNER127, PARTNER129,
PARTNER132, PARTNER134, PARTNER135, PARTNER141, PARTNER144, PARTNER151, PARTNER160,
PARTNER163, PARTNER169, PARTNER176, PARTNER177, PARTNER179, PARTNER182, PARTNER186,
PARTNER189, PARTNER196, PARTNER202, PARTNER205, PARTNER206, PARTNER215, PARTNER216,
PARTNER222, PARTNER227, PARTNER232, PARTNER244, PARTNER250, PARTNER276, PARTNER277,
PARTNER286, PARTNER288, PARTNER295, PARTNER296

## No Documented Distinguishing Rule Found

We checked the available input and tool output fields for differences between the two
Medium subgroups. We did not find any documented rule, single-field threshold, or simple
combination of available non-identifier signals that cleanly separates them.

**Categorical fields — tool outputs are identical across both groups:**
- `traffic_analysis_result`: both groups are 100% "SUSPICIOUS"
- `source_verification_result`: both groups are 100% "WARNING"
- `investigation_status`: both groups are 100% "Completed"
- `violation_type`: both groups contain the same violation-type categories; no violation
  type uniquely identifies one subgroup
- `evidence_collected`: both groups contain the same set of evidence combinations
- `top_referral_source`: both groups contain largely the same referral sources (one extra
  value, `twitter.com`, appears only in the Temporary Suspension group, but it is not
  exclusive enough to serve as a separator)

**Numeric fields — overlapping ranges, no clean threshold:**

| Field | Warning Issued (39) | Temporary Suspension (50) |
|-------|-------------------|-------------------------|
| engagement_score | [0.2, 1.5] mean=0.79 | [0.2, 1.5] mean=0.94 |
| conversion_rate | [0.006, 0.079] mean=0.041 | [0.002, 0.078] mean=0.036 |
| bounce_rate | [81.0, 97.9] mean=90.1 | [81.0, 97.7] mean=88.9 |
| earnings_amount | [0.24, 9.83] mean=4.78 | [0.22, 9.70] mean=4.95 |
| unattributed_clicks | [62, 1383] mean=642 | [58, 1499] mean=888 |

All ranges overlap completely. We found no single-threshold separator and no perfect
depth-2 decision tree over these fields that separates the two groups.

## Worked Example: PARTNER115 (CSV Line 17)

Input data:
```
partner_id=PARTNER115, risk_level=Medium, violation_type=Spoofing Traffic,
engagement_score=0.9, conversion_rate=0.024, bounce_rate=91.3
```

Tool results:
- `InvestigateViolations` → "Completed"
- `AnalyzeTrafficPatterns` → "SUSPICIOUS"
- `ValidateReferralSources` → "WARNING"
- `CalculateRiskScore` → "Medium"

Per the SOP (section 5.6): Medium risk violations → **"Temporary Suspension"**.

The CSV says **"Warning Issued"** — which the SOP only assigns to Low risk violations
with evidence.

## Root Cause

The labeled dataset appears to have been generated with a rule that is not documented in
the SOP. One possibility: the label generator used a secondary threshold (perhaps on
engagement_score, unattributed_clicks, or some composite) to subdivide Medium risk into
two enforcement tiers. But no such rule appears in the SOP text, and we did not find a
simple combination of available non-identifier fields that cleanly separates the two groups.

This is the same class of bug found in `referral_abuse_detection_v1` (9 tasks with CSV
labels following a closure-priority rule not stated in the SOP) and `order_fulfillment`
(4 tasks where tool outputs disagree with CSV ground truth).

## Verification

Running a strict SOP-following agent (Proceda with Gemini 3 Flash Preview) against all
200 tasks produces:
- **159/200 (79.5%) TSR** raw
- **159/161 (98.8%) TSR** excluding the 39 SOP/CSV-inconsistent tasks
- The 39 SOP/CSV failures all predict "Temporary Suspension" where CSV expects "Warning Issued"
- The remaining 2 failures are genuine agent reasoning errors (unrelated to this bug)

## Suggested Fix

1. **Fix the 39 labels:** Update the 39 affected rows in `test_set_with_outputs.csv` to set
   `enforcement_action = "Temporary Suspension"`, matching the SOP's explicit mapping for
   Medium risk.

2. **Or update the SOP:** If the intent is that Medium risk should sometimes map to
   "Warning Issued," add the distinguishing rule to section 5.6 with clear criteria an
   agent can evaluate.

3. **Add a regression test:** A test that verifies the SOP's stated enforcement mapping
   against all CSV labels would prevent this class of inconsistency.
