# Bug Report: warehouse_package_inspection tools use mock arithmetic instead of CSV lookups

## Summary

Two tools in the `warehouse_package_inspection` domain — `validateBarcode` and `assessPackageCondition` — use deterministic modulo arithmetic on PO numbers instead of looking up values from the CSV dataset. This causes their outputs to disagree with the ground truth CSV approximately 45% of the time, creating an artificial ceiling on benchmark scores. A third tool, `updateResolutionStatus`, has a missing state transition for the no-problem case.

Every other domain in SOP-Bench (patient_intake, dangerous_goods, customer_service, etc.) uses pandas CSV lookups to return ground-truth-consistent values. The warehouse domain is the only one that uses synthetic arithmetic.

**Impact:** A perfect agent that follows the SOP flawlessly will score at most ~53% TSR on this domain. We verified this by running an agent that achieved 100% accuracy (80/80) on tasks where tool outputs agree with CSV, and 0% accuracy (0/70) on tasks where they disagree.

## Affected Files

All paths relative to the repository root (`sop-bench/`).

**Primary:**
- `src/amazon_sop_bench/benchmarks/data/warehouse_package_inspection/tools.py`

**Reference (working pattern):**
- `src/amazon_sop_bench/benchmarks/data/patient_intake/tools.py`
- `src/amazon_sop_bench/benchmarks/data/dangerous_goods/tools.py`

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

| PO Number | `int(po[2:]) % 2` | Tool returns | CSV says |
|-----------|-------------------|-------------|----------|
| PO987654435 | 1 (odd) | `barcode_match=False` | `True` |
| PO987654494 | 0 (even) | `barcode_match=True` | `False` |
| PO987654326 | 0 (even) | `barcode_match=True` | `False` |
| PO987654447 | 1 (odd) | `barcode_match=False` | `True` |

When `barcode_match` is wrong, the entire task result is wrong: a false negative triggers an early exit to "Returned to Vendor" (skipping all subsequent steps), while a false positive causes the agent to proceed through steps that the ground truth expects to be skipped.

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

When `problem_type` is an empty list (no problems found), neither branch executes and `new_status` remains `current_status` ("Pending"). But the CSV ground truth for no-problem tasks has `resolution_status = "Resolved"`. There is no code path that produces "Resolved".

**Affected tasks:** All tasks where barcode matches, quantities match, warehouse matches, and no damage is detected. The CSV shows 14 such tasks with `resolution_status = "Resolved"`.

## Comparison with working domains

Every other domain uses pandas to look up values from the CSV dataset:

**patient_intake** (`src/amazon_sop_bench/benchmarks/data/patient_intake/tools.py`):
```python
# Line 56-64 (validateInsurance)
df = pd.read_csv(self.dataset_file_path)
patient_data = df[df["patient_id"] == patient_id]
# ... returns values from CSV row
```

**dangerous_goods** (`src/amazon_sop_bench/benchmarks/data/dangerous_goods/tools.py`):
```python
# Similar CSV lookup pattern at lines 51, 87, 123, 159
df = pd.read_csv(self.dataset_file_path)
product_data = df[df["product_id"] == product_id]
```

The warehouse domain's `WarehousePackageInspectionManager.__init__` (line 29) loads the CSV file path into `self.dataset_file_path`, matching the pattern of other domains. But unlike other domains, `validateBarcode` and `assessPackageCondition` never read from it — they compute results from PO number arithmetic instead.

The other warehouse tools (`calculateQuantityVariance`, `verifyWarehouseLocation`, `calculateChargeback`, `generateProblemReport`) use input-based deterministic logic that is consistent with the CSV data, since they operate on numeric inputs (quantities, warehouse IDs) that are passed directly from the CSV row.

## Toolspec descriptions are misleading

**File:** `src/amazon_sop_bench/benchmarks/data/warehouse_package_inspection/toolspecs.json`

The tool descriptions claim real image processing:

- `validateBarcode` (line 5): *"Validates the received product barcode against the confirmed product ID **using image processing system**."*
- `assessPackageCondition` (line 91): *"Evaluates the physical condition of received packages **using damage detection algorithm**."*

The implementations do neither. The `received_product_bar_code` and `package_image_path` parameters are accepted as strings but never opened, read, or processed.

## Measured impact

We ran an agent (Proceda with Gemini 3 Flash Preview) that follows the SOP step-by-step with 100% execution completion rate. Results:

| Subset | Tasks | Agent Accuracy |
|--------|-------|----------------|
| Both tools agree with CSV | 80 | **100% (80/80)** |
| Either tool disagrees with CSV | 70 | **0% (0/70)** |
| **Overall** | **150** | **53.3% (80/150)** |

The agent makes zero reasoning errors. Every failure traces to a tool returning a value inconsistent with the CSV ground truth. The best published baseline on this domain is 69% TSR — also depressed by the same tool bugs.

## Suggested fix

Replace the modulo arithmetic in `validateBarcode` and `assessPackageCondition` with CSV lookups matching the pattern used by all other domains:

```python
def validateBarcode(self, po_number, confirmed_product_id, received_product_bar_code):
    df = pd.read_csv(self.dataset_file_path)
    row = df[df["po_number"] == po_number].iloc[0]
    barcode_match = row["barcode_match"]
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
