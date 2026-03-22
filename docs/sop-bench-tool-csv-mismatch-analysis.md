# SOP-Bench Tool/CSV Mismatch Analysis

Last updated: 2026-03-22

## Summary

Multiple SOP-Bench domains have tool implementations that disagree with their CSV
ground truth. This analysis covers `warehouse_package_inspection` and `video_annotation`,
the two lowest-scoring domains besides `content_flagging` (which has a separate filed
issue). The pattern is the same across all three: the released tool code does not
faithfully look up precomputed values from the CSV.

## What the paper says

The paper (arxiv 2506.08119, submitted to KDD 2026) describes the benchmark design as:

> "To simulate API calls, each dataset includes precomputed inputs and outputs for
> every tool call, stored as columns. These mocks replace live APIs to enable stable,
> reproducible evaluation without runtime variability."

Per-domain results (Claude 3.5 Sonnet, from paper Table 4):

| Domain                     | FC TSR | ReAct TSR | FC C-TSR | ReAct C-TSR |
|----------------------------|--------|-----------|----------|-------------|
| Warehouse Package Inspect. | 13%    | 21%       | 32%      | 39%         |
| Video Annotation           | 49%    | 69%       | 49%      | 99%         |
| Content Flagging           | 0%     | 10%       | —        | —           |

The paper attributes low scores to agent-side failures: "skipping steps," "manually
approximating values when a tool fails," and "hallucinating results." It does not
acknowledge tool-side bugs as a contributing factor for these domains.

The discussion section mentions "inconsistent function outputs" in the context of
content flagging but frames this as an agent failure, not a data issue.

## warehouse_package_inspection: hardcoded logic ignores CSV

### The bug

Two tools compute outputs from PO-number arithmetic instead of looking up CSV values:

- `assessPackageCondition`: `damage_detected = (int(po_number[2:]) % 3 == 0)`
- `validateBarcode`: `barcode_match = (int(po_number[2:]) % 2 == 0)`

These are deterministic but **wrong** — they don't match the precomputed CSV ground
truth. The other five tools (`calculateQuantityVariance`, `calculateChargeback`,
`verifyWarehouseLocation`, `generateProblemReport`, `updateResolutionStatus`) compute
from their input arguments rather than CSV lookups, which is less obviously wrong but
still means the agent can't recover correct intermediate values once upstream tools
return incorrect data.

### Quantified impact

Against the 150-row CSV (`test_set_with_outputs.csv`):

| Check                         | Match rate |
|-------------------------------|-----------|
| `assessPackageCondition` correct | 86/150 (57.3%) |
| `validateBarcode` correct       | 82/150 (54.7%) |
| Both correct                    | 45/150 (30.0%) |

Since `resolution_status` (the evaluated output column) depends on barcode match
(mismatch -> "Returned to Vendor") and damage assessment (feeds chargeback and
problem report), 70% of tasks have at least one upstream tool giving the agent
incorrect information. An agent that follows the SOP perfectly will still get the
wrong answer on those tasks.

### Task count mismatch

README claims 200 tasks. CSV contains 150 rows.

## video_annotation: 20 of 26 tools are stubs

### The bug

Of the 26 tool methods in `VideoProcessingManager`, 20 are stubs that contain only
`pass` and return `None`. Only 6 tools have actual implementations with return values.

The 20 stub tools include core functions like `processHighResolution`,
`validateOutputFormat`, `checkProcessingStatus`, `optimizeTrackingSettings`,
`analyzeCameraStability`, `validateSceneContext`, and others.

When the agent calls a stub tool, it receives `None`, which it must then work around
by hallucinating or skipping the step.

### Quantified impact

The ReAct agent achieves 99% C-TSR (conditional on execution completing) but only
70% ECR (execution completion rate), yielding 69% TSR. The 30% execution failure rate
is consistent with agents crashing or stalling when tools return `None`.

The `random.shuffle(toolspec_json)` in `__init__` randomizes tool presentation order
across runs, adding non-determinism, though this doesn't affect tool output correctness.

### Task count mismatch

README claims 168 tasks. CSV contains 125 rows.

## Is there a pattern?

Yes. The three domains with the lowest baseline scores all have tool/CSV mismatches:

| Domain                     | Best baseline TSR | Bug type                       |
|----------------------------|-------------------|--------------------------------|
| Content Flagging           | 10% (ReAct)       | `random.random()` in tools, CSV formula mismatch |
| Warehouse Package Inspect. | 21% (ReAct)       | Hardcoded modular arithmetic ignores CSV |
| Video Annotation           | 69% (ReAct)       | 20/26 tools are `pass` stubs |

Other domains (customer_service, dangerous_goods, email_intent, know_your_business,
patient_intake, aircraft_inspection) have zero stub tools in their `tools.py`.

## Is this acknowledged?

- **GitHub issues**: Issue #2 (filed by us) covers `content_flagging`. No existing
  issues for warehouse or video_annotation.
- **Paper**: Does not acknowledge tool bugs. Attributes low scores to agent reasoning
  failures.
- **README/docs**: No caveats about specific domains.

## Assessment

These are bugs, not intentional benchmark difficulty. Evidence:

1. The paper explicitly promises "stable, reproducible evaluation without runtime
   variability" via precomputed mock tools.
2. The paper's own tool-generation prompt (Appendix C.5) instructs that tools should
   "use only existing dataset columns."
3. `ADDING_BENCHMARKS.md` uses random outputs as an example of what NOT to do.
4. Stub tools returning `None` are clearly unfinished, not a design choice.
5. The hardcoded `po_number % 3` / `po_number % 2` logic in warehouse is a placeholder
   that was never replaced with CSV lookups.

The published baseline numbers for these three domains are artificially depressed by
data bugs, not just agent limitations. Any external system evaluated against these
domains will face the same ceiling.
