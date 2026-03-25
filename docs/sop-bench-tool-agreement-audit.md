# SOP-Bench Tool/CSV Agreement Audit

Audit of whether mock tool implementations produce outputs consistent with CSV ground truth.

## Summary

| Domain | Best Baseline TSR | Tool Type | Stubs | Tool/CSV Agreement | Mismatch Source |
|--------|-------------------|-----------|-------|--------------------|-----------------|
| patient_intake | 100% | CSV lookup | 0/7 | 100% | — |
| aircraft_inspection | 99% | CSV lookup | 0/8 | 100% | — |
| email_intent | 99% | CSV lookup | 0/6 | 100% | — |
| referral_abuse_v1 | 98% | CSV lookup | 0/4 | 100% | — |
| referral_abuse_v2 | 98% | CSV lookup | 0/7 | 100% | — |
| video_classification | 95% | CSV lookup | 5/11 | ~100%* | 5 stub tools return None |
| dangerous_goods | 87% | CSV lookup | 0/5 | 100% | — |
| traffic_spoofing | 86% | CSV lookup | 0/7 | 100% | — |
| customer_service | 79% | CSV lookup | 0/11 | 100% | — |
| order_fulfillment | — | CSV lookup | 0/5 | 100% | — |
| warehouse_inspection | 69% | Deterministic | 0/8 | ~55% | `po_number % 3` and `% 2` |
| content_flagging | 60% | Random | 0/6 | ~50% | `random.random()` for BPI and device consistency |
| video_annotation | 58% | Mixed | 20/27 | ~86% | 20 stub tools return None; SOP has ambiguous env rules |
| know_your_business | 58% | CSV lookup | 0/10 | 100% | — |

*video_classification: implemented tools read from CSV correctly, but 5 of 11 tools are stubs returning None.

## Detailed Findings

### warehouse_package_inspection (69% best baseline)

Two tools use hardcoded deterministic logic instead of reading from CSV:

- **`assessPackageCondition`**: `damage_detected = (int(po_number[2:]) % 3 == 0)` — agrees with CSV `package_condition` only **57.3%** of the time (86/150).
- **`verifyBarcodeMatch`**: `barcode_match = (int(po_number[2:]) % 2 == 0)` — agrees with CSV `barcode_match` only **54.7%** of the time (82/150).

These two tools feed into downstream decisions (chargeback, resolution_status), so the ~55% agreement on inputs creates an artificial ceiling well below 100%.

### content_flagging (60% best baseline)

Two tools use `random.random()`:

- **`calculate_device_consistency`**: returns `random.random()` — completely uncorrelated with any CSV field.
- **`calculateBotProbabilityIndex`**: BPI is set to `random.random()`, then adjusted by device_consistency. Both values are random.

The final decision depends on these scores, so the tool output is non-deterministic and uncorrelated with ground truth. Expected agreement with CSV: ~50%.

### video_annotation (58% best baseline)

**20 of 27 tools are stubs** (method body is just `pass`, returns None). The 7 implemented tools (`validateVideoFormat`, `validateLidarData`, `performObjectDetection`, `executeSegmentation`, `runAutomatedQC`, `performHumanValidation`, `process_tool_call`) all read correctly from the CSV.

The problem is different from warehouse_inspection: the tools that work are faithful, but the SOP contains ambiguous validation rules that the LLM must infer from vague prose. Specifically, Section 5.1 says "Environmental constraints mandate urban setting contexts with daylight illumination conditions and front-camera positioning," but the data includes:

- **Non-urban scenes**: interstate, freeway, car park, loading dock, park and ride, tunnel, etc.
- **Non-daylight lighting**: pitch black, moon out, starry, lamp, dark, dim, twilight, LEDs
- **Non-front cameras**: birds eye, trunk, driver assist rev, side right, side left, all in one

Applying all stated SOP thresholds yields 86.4% agreement (108/125). All 17 disagreements are cases where every numeric threshold passes but CSV says False. These 17 cases all have non-standard scene/lighting/camera values that violate the ambiguous environmental constraints. The stub tools compound this: the LLM calls tools like `validateWeatherConditions` or `analyzeCameraStability` and gets None back, losing information it needs for the decision.

### High-scoring domains: patient_intake (100%), referral_abuse (98%), aircraft_inspection (99%)

All tools read directly from CSV via pandas lookup. No stubs, no random values, no deterministic mocks. The tool outputs are always consistent with the ground truth data, so the agent just needs to follow the SOP logic correctly.

## Correlation: Mismatch Rate vs Baseline TSR

| Domain | Tool/CSV Agreement | Best Baseline TSR |
|--------|-------------------|-------------------|
| patient_intake | 100% | 100% |
| aircraft_inspection | 100% | 99% |
| email_intent | 100% | 99% |
| referral_abuse_v1 | 100% | 98% |
| referral_abuse_v2 | 100% | 98% |
| video_classification | ~100%* | 95% |
| dangerous_goods | 100% | 87% |
| traffic_spoofing | 100% | 86% |
| customer_service | 100% | 79% |
| warehouse_inspection | ~55% | 69% |
| content_flagging | ~50% | 60% |
| video_annotation | ~86% | 58% |
| know_your_business | 100% | 58% |

The three lowest-scoring domains (warehouse_inspection, content_flagging, video_annotation) are the only three with tool/CSV mismatches. The correlation is clear but not perfect: KYB scores 58% despite having faithful tools (its difficulty comes from subjective judgment calls, not tool bugs).

Video annotation's low baseline is a combination of: (1) 20 stub tools returning None, (2) ambiguous environmental validation rules, and (3) an extremely long SOP (350 lines of bureaucratic prose). The tool mismatch is not the primary problem the way it is for warehouse_inspection and content_flagging.

## Conclusion

Three of 14 domains have tool implementations that disagree with CSV ground truth:

1. **warehouse_package_inspection** — Deterministic mocks (`% 2`, `% 3`). Ceiling: ~55%.
2. **content_flagging** — Random values (`random.random()`). Ceiling: ~50%.
3. **video_annotation** — 20/27 stub tools return None. Faithful tools agree ~86%, but stubs + SOP ambiguity create the remaining gap.

All other domains have 100% tool/CSV agreement. Low scores in those domains (e.g., KYB at 58%) are due to reasoning difficulty, not tool bugs.
