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

### Dominant failure: "awaiting information" predicted as "escalate" (31/52 failures)

This is 60% of all failures. The model correctly identifies red flags (sanctions matches, shell companies, offshore jurisdictions, flagged bank accounts) but escalates instead of requesting more information.

The SOP's Step 1 says: "If you believe that there are some irregularities here, please set the status as 'awaiting information' so that associates can reach out to these businesses for additional data." This refers specifically to irregularities in the business profile — mismatched names, suspicious websites, incomplete addresses, invalid emails.

The distinction between "escalate" and "awaiting information" is subtle and judgment-dependent:
- **Escalate**: Clear policy violations (sanctions match, expired license >42 days, invalid TIN format)
- **Awaiting information**: Profile data looks suspicious but isn't conclusively fraudulent — could be typos or data entry errors

The model tends to see the red flags from downstream tools (sanctions, shell company, offshore jurisdiction) and jumps to "escalate," overriding the earlier Step 1 assessment that the profile irregularities warrant requesting more information first. In the one task where the model correctly predicted "awaiting information" (biz_007), it explicitly referenced "missing information and irregularities found in the business profile (invalid email format and incomplete address)" in its final step summary.

This is a reasoning failure, not a data problem: the tool results are correct, and the model has all the information it needs to distinguish the two categories. The SOP's instructions for when to use "awaiting information" vs "escalate" are inherently ambiguous — many of these businesses have both profile irregularities AND sanctions/PEP matches, and the correct answer requires prioritizing the profile issues over the downstream findings.

### Extraction failures (12/52 failures)

8 tasks produced `<missing>` (no output extracted) and 4 produced garbage values ("Flagged", "Active", "false", "No") — the model emitted a field from tool results instead of the escalation status. These 12 extraction failures are split across all expected categories.

The garbage values suggest the output extractor matched XML tags containing tool result data rather than the actual `escalation_status` field. This could be improved with stricter extraction logic.

### Over-cautious "awaiting information" (6/52 failures)

6 "approve" tasks were incorrectly predicted as "awaiting information." The model flagged minor profile issues that the ground truth considered acceptable, requesting additional data when the business should have been approved.

### Missed escalations (3/52 failures)

2 "escalate" tasks were predicted "approve" and 1 was predicted "awaiting information." These are cases where the model missed or underweighted genuine red flags.

## Why This Domain Is Hard

KYB is the hardest domain with working tools in SOP-Bench (best baseline 58%). The difficulty comes from:

1. **Subjective judgment**: The SOP explicitly says "use your experience" multiple times. Whether a business name mismatch is a typo or fraud is inherently ambiguous.

2. **Three-way classification**: Most domains are binary (approve/reject) or have clear formulaic thresholds. KYB requires distinguishing three categories where two of them (escalate vs awaiting information) have overlapping signals.

3. **Conflicting signals**: Many tasks have both profile irregularities (suggesting "awaiting information") AND sanctions/compliance failures (suggesting "escalate"). The correct answer depends on which signal the SOP intends to prioritize.

4. **Noisy risk scores**: The SOP explicitly says "the risk scores are not reliable" and asks the agent to document whether their judgment aligns. This is deliberately designed to test independent reasoning rather than threshold-following.

5. **12 steps with 65+ LLM calls per task**: The long execution pipeline means more opportunities for the model to lose track of earlier findings by the time it reaches the final determination step.

## Configuration

- Model: `openrouter/google/gemini-3.1-pro-preview`
- Temperature: 0.0
- Workers: 50
- Average task time: ~6 minutes (range: 2-23 minutes)
- Total run time: ~25 minutes
