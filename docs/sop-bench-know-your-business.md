# SOP-Bench: Know Your Business

**TSR: 42.2% (38/90) | ECR: 100% | Model: Gemini 3.1 Pro via OpenRouter**

Best baseline: 58% (Claude 4.5 Opus ReAct). Below baseline by 16 points.

## Results

| Expected | Count | Correct | Accuracy |
|----------|-------|---------|----------|
| approve | 32 | 20 | 62.5% |
| escalate | 24 | 17 | 70.8% |
| awaiting information | 34 | 1 | 2.9% |

## Confusion Matrix

|  | pred: approve | pred: escalate | pred: awaiting info | pred: other/missing |
|--|---------------|----------------|---------------------|---------------------|
| **exp: approve** | **20** | 0 | 6 | 6 |
| **exp: escalate** | 2 | **17** | 1 | 4 |
| **exp: awaiting info** | 0 | **31** | **1** | 2 |

## Failure Analysis

### Dominant failure: "awaiting information" labeled tasks have stronger escalation signals than "escalate" tasks (31/52 failures)

60% of all failures are the model predicting "escalate" when the ground truth says "awaiting information." This initially looks like a reasoning error, but examining the CSV data reveals something unexpected:

**All 34 "awaiting information" tasks** have `shell_company_suspected=True`, `offshore_jurisdiction_flag=True`, sanctions matches, and PEP flags. Their risk scores range from 0.85 to 1.00 (mean 0.93).

**Only 16 of 24 "escalate" tasks** have shell/offshore flags. 8 "escalate" tasks have zero flags (clear sanctions, no shell, no offshore). Risk scores range from 0.15 to 0.98 (mean 0.66).

| Signal | "awaiting info" (34) | "escalate" (24) | "approve" (32) |
|--------|---------------------|-----------------|----------------|
| shell_company=True | **34/34 (100%)** | 16/24 (67%) | 0/32 (0%) |
| offshore=True | **34/34 (100%)** | 16/24 (67%) | 0/32 (0%) |
| sanctions matched | **~34/34** | ~16/24 | 0/32 |
| mean risk_score | **0.93** | 0.66 | 0.18 |

The "awaiting information" category has **strictly more red flags and higher risk** than the "escalate" category. An agent faithfully following the SOP — which says to escalate on sanctions matches, shell companies, offshore jurisdictions, and expired licenses — will rationally predict "escalate" for these tasks.

The SOP's Step 1 does say to set "awaiting information" for profile irregularities (bad emails, suspicious addresses, mismatched names). But the SOP also says to escalate on sanctions matches (Step 7), shell companies (Step 6), and offshore flags (Step 4). When a task has both profile irregularities AND multiple hard escalation triggers, the SOP gives no clear priority rule. The CSV ground truth appears to follow an implicit rule — that profile irregularities override all downstream findings — but this rule is not stated in the SOP.

This is the same pattern found in referral_abuse_v1 (9 tasks), traffic_spoofing (39 tasks), and order_fulfillment (4 tasks): **the CSV ground truth follows a labeling rule that contradicts or extends the written SOP.** An agent that follows the SOP faithfully gets penalized.

### Adjusted accuracy

If we exclude the 31 tasks where the model correctly identified escalation triggers but the CSV expects "awaiting information":
- **Remaining failures**: 21/90
- **Adjusted TSR**: 76.7% (69/90)
- **On SOP-consistent tasks**: ~69/59 is not meaningful since we can't cleanly separate them

A more precise framing: on the 56 tasks where the expected label is "approve" or "escalate" (categories with clear SOP rules), the model achieves **37/56 = 66.1%**. The remaining 19 failures on these tasks are a mix of extraction failures (10) and genuine reasoning errors (9).

### Extraction failures (12/52 failures)

8 tasks produced `<missing>` (no output extracted) and 4 produced garbage values ("Flagged", "Active", "false", "No") — the model emitted a tool result field instead of the escalation status. These 12 extraction failures are split across all expected categories.

### Over-cautious "awaiting information" (6/52 failures)

6 "approve" tasks were incorrectly predicted as "awaiting information." The model flagged minor profile issues that the ground truth considered acceptable.

### Missed escalations (3/52 failures)

2 "escalate" tasks were predicted "approve" and 1 was predicted "awaiting information."

## Why This Domain Is Hard

KYB is the hardest domain with working tools in SOP-Bench (best baseline 58%). The difficulty comes from:

1. **Ambiguous labeling rules**: The CSV ground truth follows an implicit priority rule (profile irregularities → "awaiting information" regardless of downstream findings) that isn't in the SOP. This creates an artificial ceiling for SOP-faithful agents.

2. **Subjective judgment**: The SOP explicitly says "use your experience" multiple times. Whether a business name mismatch is a typo or fraud is inherently ambiguous.

3. **Three-way classification**: Most domains are binary or have clear formulaic thresholds. KYB requires distinguishing three categories where two of them (escalate vs awaiting information) have overlapping — and inverted — signals.

4. **Noisy risk scores**: The SOP explicitly says "the risk scores are not reliable." This is deliberately designed to test independent reasoning rather than threshold-following.

5. **12 steps with 65+ LLM calls per task**: The long execution pipeline means more opportunities for the model to lose track of earlier findings.

## Configuration

- Model: `openrouter/google/gemini-3.1-pro-preview`
- Temperature: 0.0
- Workers: 50
- Average task time: ~6 minutes (range: 2-23 minutes)
- Total run time: ~25 minutes
