# Bug Report: know_your_business — CSV labels for "awaiting information" contradict SOP escalation rules

## Summary

In the `know_your_business` domain, all 34 tasks labeled "awaiting information" in the CSV have stronger escalation signals than the majority of tasks labeled "escalate." An agent that faithfully follows the SOP's explicit escalation rules will predict "escalate" for these tasks and be scored as incorrect.

## Evidence

The SOP defines clear escalation triggers:
- Step 3: Escalate if TIN format is invalid or license expired >42 days
- Step 4: Pay attention to `offshore_jurisdiction_flag`
- Step 6: Evaluate `shell_company_suspected`
- Step 7: Escalate on sanctions matches and PEP status
- Step 12: "Triggering any of the above checks" → escalate

The CSV ground truth for the three categories:

| Signal | "awaiting info" (34 tasks) | "escalate" (24 tasks) | "approve" (32 tasks) |
|--------|---------------------------|----------------------|---------------------|
| shell_company_suspected=True | **34/34 (100%)** | 16/24 (67%) | 0/32 (0%) |
| offshore_jurisdiction_flag=True | **34/34 (100%)** | 16/24 (67%) | 0/32 (0%) |
| At least one sanctions "Matched" | **~34/34** | ~16/24 | 0/32 |
| Mean risk_score | **0.93** | 0.66 | 0.18 |
| registration_status=Inactive | 17/34 (50%) | 6/24 (25%) | 0/32 (0%) |

Every "awaiting information" task has shell company suspected, offshore jurisdiction, and sanctions matches. Only two-thirds of "escalate" tasks have these signals. Eight "escalate" tasks have *zero* of these flags (clear sanctions, no shell, no offshore, Active registration) — their risk scores are as low as 0.15.

The SOP's Step 12 says: "Determine `escalation_status` based on cumulative risk assessment, triggering 'escalate' status if your review triggers any of the above checks." Under this rule, all 34 "awaiting information" tasks should be "escalate."

## The implicit rule

The SOP's Step 1 says: "If you believe that there are some irregularities here, please set the status as 'awaiting information' so that associates can reach out to these businesses for additional data." This refers to profile-level issues (mismatched names, suspicious websites, incomplete addresses).

The CSV labels appear to follow an implicit priority rule: if the business profile has irregularities in Step 1, the final status is "awaiting information" regardless of what downstream tools find (sanctions, shell companies, etc.). This priority rule is not stated in the SOP. In fact, it contradicts Step 12's instruction to escalate "if your review triggers any of the above checks."

## Impact on benchmark scores

We evaluated this domain with Gemini 3.1 Pro (Proceda, 90 tasks):
- **Raw TSR**: 42.2% (38/90)
- **On SOP-consistent tasks** (excluding the 31 disagreements): 64.4% (38/59)

The best published baseline is 58% (Claude 4.5 Opus ReAct). It is unclear how much of the gap between top baselines and 100% is attributable to this labeling issue vs genuine reasoning difficulty.

This is consistent with a pattern across several SOP-Bench domains where CSV ground truth follows labeling rules not present in the SOP:
- `referral_abuse_detection_v1`: 9 tasks follow a closure-priority rule not in the SOP ([issue #4](https://github.com/amazon-science/SOP-Bench/issues/4))
- `traffic_spoofing_detection`: 39 tasks labeled "Warning Issued" for Medium risk when SOP says "Temporary Suspension" ([issue #5](https://github.com/amazon-science/SOP-Bench/issues/5))

## Suggested Fix

Either:
1. Update the SOP to explicitly state the priority rule: "If Step 1 identifies profile irregularities requiring additional data, set status to 'awaiting information' even if downstream checks trigger escalation criteria." This would make the labels consistent with the SOP.
2. Relabel the 34 "awaiting information" tasks based on the SOP's current rules (most would become "escalate").

## Environment

- SOP-Bench commit: `156e9ecd60f42c43e4f3a12824e466afff21e9d8` (2026-02-22, initial release)
- Domain: `know_your_business`
- Files examined: `test_set_with_outputs.csv`, `sop.txt`
- Paper: SOP-Bench v2 (2026-02-23), https://ar5iv.labs.arxiv.org/html/2506.08119
