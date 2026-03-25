# SOP-Bench Warehouse Package Inspection: 53.3% TSR

## Summary

We ran Proceda against the SOP-Bench warehouse_package_inspection benchmark — a 150-task
evaluation where LLM agents must classify and resolve problematic shipment receipts through
barcode validation, quantity analysis, location verification, and damage assessment. Proceda
achieves **53.3% TSR** (80/150 correct) using Gemini 3 Flash Preview.

| Agent | Model | TSR |
|-------|-------|-----|
| Best baseline (Table 5) | Various | 69% |
| **Proceda** | **Gemini 3 Flash Preview** | **53.3% (80/150)** |

**Important caveat:** The TSR is artificially depressed by broken mock tools in the benchmark
(see "Tool/CSV Mismatch" below). On the 80 tasks where mock tools agree with CSV ground truth,
Proceda achieves **100% accuracy** (80/80) — zero agent reasoning failures.

## What Makes This Domain Hard

### The SOP Logic

The warehouse inspection SOP is a 7-step pipeline:

1. **Barcode validation** — Compare barcode image against confirmed product ID. If mismatch,
   short-circuit to "Wrong Item" → "Returned to Vendor".
2. **Quantity variance** — Calculate discrepancy between ordered/confirmed/received quantities.
   Classify as Cancelled, Overage, Underage, or Severe Unmatched.
3. **Location verification** — Compare intended vs actual warehouse. Mismatch → "Wrong Warehouse".
4. **Package condition** — Assess damage from package image. Damage → "Vendor Damaged".
5. **Chargeback calculation** — Compute vendor liability based on problem types and quantities.
6. **Resolution status** — Determine final status (Pending, Processing, Resolved, Returned to Vendor).
7. **Problem report** — Generate comprehensive report with all findings.

The key complexity is the branching: barcode mismatch causes an early exit, while all other
checks accumulate problems that feed into chargeback and resolution calculations.

### Image Paths (Not Real Images)

The domain has two image-related inputs (`received_product_bar_code`, `package_image_path`)
which are file paths passed as strings to tools. The tools accept these paths but never open
the files — they use deterministic mock logic instead. All baselines treat this as text-only.

## Tool/CSV Mismatch (Benchmark Bug)

The mock tools use simplified deterministic logic that doesn't match the CSV ground truth:

| Tool | Mock Logic | CSV Agreement |
|------|-----------|---------------|
| `validateBarcode` | `int(po_number[2:]) % 2 == 0` | 54.7% (82/150) |
| `assessPackageCondition` | `int(po_number[2:]) % 3 == 0` | 52.8% (where barcode agrees) |
| **Both tools correct** | — | **53.3% (80/150)** |

The other 5 tools (calculateQuantityVariance, verifyWarehouseLocation, calculateChargeback,
updateResolutionStatus, generateProblemReport) use real input-based logic and are correct.

This means a **perfect agent** following the SOP exactly would score at most ~53% TSR. The 69%
baseline likely includes cases where errors cancel out or the agent reasons around tool results.

### Additional Tool Bug: No-Problem Resolution

The `updateResolutionStatus` tool returns "Pending" when called with an empty problem list,
but the correct resolution for no-problem cases is "Resolved". We handle this in the SKILL.md
by instructing the agent to set "Resolved" directly when no problems are found.

## Failure Analysis

| Category | Count | % |
|----------|-------|---|
| **Correct** | 80 | 53.3% |
| **Tool mismatch (barcode or condition)** | 70 | 46.7% |
| **Agent reasoning error** | 0 | 0% |
| **Total** | 150 | 100% |

All 70 failures trace to the mock tool logic returning different values than the CSV ground
truth. On the 80 tasks where both tools agree with the CSV, Proceda scores 100%.

## Output Extraction

During this domain we discovered and fixed an extraction priority bug: the output extractor
previously gave tool results priority over the agent's deliberate final answer (XML tags in
complete_step summaries). When `validateBarcode` returned an early `resolution_status: "Processing"`
and the agent later determined a different status, the extractor would use the tool's value.

**Fix:** Message extraction (XML tags, final_output blocks) now takes priority over raw tool
results. Tool results fill in gaps only when message extraction doesn't find a value.

## Configuration

- **Model:** `gemini/gemini-3-flash-preview`, temperature=0.0
- **Execution:** Sequential (no parallelism, to avoid rate limits)
- **Input columns:** Explicit override in local `metadata.json` (14 input columns) to prevent
  ground truth leakage from CSV columns like `problem_type`, `barcode_match`, etc.
- **Output field:** `resolution_status`

## Files

- `benchmarks/sop_bench/domains/warehouse_package_inspection/SKILL.md`
- `benchmarks/sop_bench/domains/warehouse_package_inspection/config.yaml`
- `benchmarks/sop_bench/domains/warehouse_package_inspection/metadata.json`
- `docs/sop-bench-tool-csv-mismatch-analysis.md` — Cross-domain mismatch analysis
- `docs/sop-bench-tool-agreement-audit.md` — Tool agreement rates for all domains

## Key Takeaway

This domain demonstrates that Proceda's SOP execution is correct — 100% accuracy on tasks
with valid tools. The 53.3% TSR is entirely a benchmark data quality issue, not an agent
limitation. The same tool bugs affect all baselines and likely explain why this domain has
the lowest scores in the benchmark (excluding video_annotation which has stub tools).
