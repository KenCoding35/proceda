# Bug Report: warehouse_package_inspection tools use mock arithmetic instead of CSV lookups

## Summary

Two tools in the `warehouse_package_inspection` domain — `validateBarcode` and `assessPackageCondition` — use deterministic modulo arithmetic on PO numbers instead of looking up values from the CSV dataset. This causes their outputs to disagree with the ground truth CSV approximately 45% of the time, creating an artificial ceiling on benchmark scores. A third tool, `updateResolutionStatus`, has a missing state transition for the no-problem case. Additionally, the CSV dataset itself contains internal contradictions.

**Per-tool agreement with CSV:**
- `validateBarcode`: 82/150 (54.7%)
- `assessPackageCondition`: 86/150 (57.3%)
- Both tools simultaneously correct: 45/150 (30.0%)

In private benchmark runs, I found that an agent following the SOP step-by-step with 100% execution completion scored only 75/150 (50.0%) overall. All 75 failures trace to tool/CSV disagreement or CSV internal inconsistency — not to agent reasoning errors.

## Affected Files

All paths relative to the repository root.

- `src/amazon_sop_bench/benchmarks/data/warehouse_package_inspection/tools.py`
- `src/amazon_sop_bench/benchmarks/data/warehouse_package_inspection/test_set_with_outputs.csv`
- `src/amazon_sop_bench/benchmarks/data/warehouse_package_inspection/toolspecs.json`

## Bug 1: `validateBarcode` uses `po_number % 2` instead of CSV lookup

**File:** `src/amazon_sop_bench/benchmarks/data/warehouse_package_inspection/tools.py`
**Method:** `validateBarcode` (line 327)
**Bug location:** Line 357

```python
# Use deterministic logic for testing (based on PO number)
barcode_match = (int(po_number[2:]) % 2 == 0)
```

This formula computes `barcode_match` from the PO number's numeric suffix modulo 2. It ignores the `confirmed_product_id` and `received_product_bar_code` parameters entirely.

**Agreement with CSV ground truth:** 82/150 tasks (54.7%).

Concrete examples of disagreement:

| PO Number | `int(po[2:]) % 2` | Tool returns | CSV `barcode_match` |
|-----------|-------------------|-------------|----------|
| PO987654435 | 1 (odd) | `False` | `True` |
| PO987654494 | 0 (even) | `True` | `False` |
| PO987654326 | 0 (even) | `True` | `False` |
| PO987654447 | 1 (odd) | `False` | `True` |

A barcode mismatch triggers the SOP's early-exit path ("Wrong Item" → "Returned to Vendor", skip all subsequent steps), so a disagreement on this tool typically produces a completely wrong `resolution_status`.

For comparison, other domains like `patient_intake` and `dangerous_goods` use pandas CSV lookups:

```python
# patient_intake/tools.py, lines 56-64 (validateInsurance)
df = pd.read_csv(self.dataset_file_path)
patient_data = df[df["patient_id"] == patient_id]
# ... returns values directly from CSV row
```

The warehouse domain's `__init__` (line 29) loads `self.dataset_file_path` following the same pattern, but `validateBarcode` never reads from it.

## Bug 2: `assessPackageCondition` uses `po_number % 3` instead of CSV lookup

**File:** `src/amazon_sop_bench/benchmarks/data/warehouse_package_inspection/tools.py`
**Method:** `assessPackageCondition` (line 49)
**Bug location:** Line 76

```python
# Use deterministic logic for testing (based on PO number)
damage_detected = (int(po_number[2:]) % 3 == 0)
```

Same pattern as Bug 1. The `package_image_path` parameter is accepted but never used.

**Agreement with CSV ground truth:** 86/150 tasks (57.3%).

## Bug 3: `updateResolutionStatus` missing "Resolved" transition

**File:** `src/amazon_sop_bench/benchmarks/data/warehouse_package_inspection/tools.py`
**Method:** `updateResolutionStatus` (line 377)
**Bug location:** Lines 413-424

```python
new_status = current_status  # line 414

if "Wrong Item" in problem_type:
    new_status = "Returned to Vendor"
elif len(problem_type) > 0:
    if current_status == "Pending":
        new_status = "Processing"
    elif current_status == "Returned to Vendor":
        raise ValueError(...)
```

When `problem_type` is an empty list (no problems found), neither branch executes and `new_status` remains `current_status` (typically "Pending"). There is no code path that produces "Resolved".

The CSV contains 22 no-problem rows (barcode matches, quantities match, warehouse matches, no damage). Of these, 14 have `resolution_status = "Resolved"` — which the tool cannot produce. The remaining 8 are internally inconsistent in the CSV itself (see next section).

## CSV internal contradictions

The ground truth CSV contains rows that are inconsistent with the SOP's own logic. There are 8 rows where all checks pass (barcode matches, quantities equal, warehouse matches, package undamaged, empty problem list), yet `resolution_status = "Returned to Vendor"` and `chargeable = True` with `charge_back_amt = 0.0`.

Examples:

| PO Number | CSV Row | barcode_match | problem_type | resolution_status | chargeable |
|-----------|---------|---------------|-------------|-------------------|------------|
| PO987654438 | 6 | True | [] | Returned to Vendor | True |
| PO987654461 | 8 | True | [] | Returned to Vendor | True |
| PO987654483 | 24 | True | [] | Returned to Vendor | True |
| PO987654421 | 30 | True | [] | Returned to Vendor | True |
| PO987654444 | 67 | True | [] | Returned to Vendor | True |
| PO987654393 | 111 | True | [] | Returned to Vendor | True |
| PO987654455 | 113 | True | [] | Returned to Vendor | True |
| PO987654427 | 147 | True | [] | Returned to Vendor | True |

Per the SOP, when all checks pass and no problems are found, the resolution should not be "Returned to Vendor." These rows appear to be data generation artifacts.

## Toolspec descriptions are misleading

**File:** `src/amazon_sop_bench/benchmarks/data/warehouse_package_inspection/toolspecs.json`

The tool descriptions claim real image processing:

- `validateBarcode` (line 5): *"Validates the received product barcode against the confirmed product ID **using image processing system**."*
- `assessPackageCondition` (line 91): *"Evaluates the physical condition of received packages **using damage detection algorithm**."*

The implementations do neither. The `received_product_bar_code` and `package_image_path` parameters are accepted as strings but never opened, read, or processed. (This is consistent with how the baseline agents use the domain — they pass image paths as plain text strings and never load or encode the actual image files.)

## Suggested fix

Replace the modulo arithmetic in `validateBarcode` and `assessPackageCondition` with CSV lookups matching the pattern used by other domains:

```python
def validateBarcode(self, po_number, confirmed_product_id, received_product_bar_code):
    df = pd.read_csv(self.dataset_file_path)
    row = df[df["po_number"] == po_number].iloc[0]
    barcode_match = bool(row["barcode_match"])
    # ... rest of logic using barcode_match from CSV
```

For `updateResolutionStatus`, add a branch for the empty problem list:

```python
if len(problem_type) == 0:
    new_status = "Resolved"
elif "Wrong Item" in problem_type:
    new_status = "Returned to Vendor"
elif len(problem_type) > 0:
    # ... existing logic
```

The 8 internally contradictory CSV rows would also need to be corrected — either by fixing `resolution_status` to "Resolved" or by adding the missing problem types that would justify "Returned to Vendor."
