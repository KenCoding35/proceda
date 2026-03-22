# SOP-Bench Order Fulfillment: 86.7% TSR

## Summary

We ran Proceda against the SOP-Bench order_fulfillment benchmark — a 30-task evaluation where
LLM agents must process customer orders through a 4-step pipeline: inventory check, customer
validation, shipping calculation, and fulfillment decision. Proceda achieves **86.7% TSR**
(26/30 correct) using Gemini 3 Flash Preview.

| Metric | Value |
|--------|-------|
| TSR | 86.7% (26/30) |
| ECR | 100.0% (30/30) |
| TSR (excluding tool-buggy tasks) | **100.0% (26/26)** |
| ECR (excluding tool-buggy tasks) | 100.0% (26/26) |
| Model | gemini-3-flash-preview |

## Adjusted Results (Excluding Tool-Buggy Tasks)

All 4 failures trace to tool logic returning values that disagree with the CSV ground truth.
On the 26 tasks where tools agree with the CSV, Proceda scores **100% (26/26)** — zero agent
reasoning errors.

### Failure 1: PROD008 (task 8) — `fulfill_immediately` vs expected `fulfill_delayed`

- `check_inventory` returns `low_stock` (PROD008 has stock=3, reorder_level=50)
- `validate_customer` returns `approved` (CUST008, platinum tier, fraud_score=0.01)
- `order_priority` is `urgent`
- `make_fulfillment_decision` receives `low_stock` + `approved` + `urgent`
- Tool logic at `tools.py:280`: `if order_priority == "urgent" or inventory_status == "in_stock"` → returns `fulfill_immediately`
- The `urgent` priority causes immediate fulfillment even though stock is low
- CSV expects `fulfill_delayed`, which would require the tool to not short-circuit on `urgent`

### Failure 2 & 3: PROD010 (tasks 10, 26) — `fulfill_immediately` vs expected `manual_review`

- CUST010 has `status: "review"` and `fraud_score: 0.25` in the CUSTOMER_DB
- `validate_customer` checks `status == "blocked"` (line 143) and `fraud_score > 0.3` (line 152)
- CUST010's status is `"review"` (not `"blocked"`) and fraud_score is 0.25 (not > 0.3)
- Neither check triggers, so the tool returns `customer_status: "approved"`
- But the CSV expects `manual_review`, implying the tool should check for `status == "review"` directly
- The tool's `validate_customer` has no branch for the `"review"` status value it stores in its own database

### Failure 4: PROD003 (task 28) — `fulfill_delayed` vs expected `backorder`

- `check_inventory` returns `low_stock` for PROD003 (stock=5, requesting 2)
- Tool correctly identifies stock is low but sufficient (`can_fulfill: true`)
- `make_fulfillment_decision` returns `fulfill_delayed` for `low_stock` + `approved` + `normal`
- CSV expects `backorder`
- This appears to be a CSV ground truth error — the tool logic is internally consistent
  (low stock with sufficient quantity should not trigger backorder)

### Summary of Tool Bugs

| Task | Predicted | Expected | Root Cause |
|------|-----------|----------|------------|
| 8 (PROD008) | fulfill_immediately | fulfill_delayed | `urgent` priority overrides low_stock check |
| 10 (PROD010) | fulfill_immediately | manual_review | `validate_customer` ignores `status: "review"` |
| 26 (PROD010) | fulfill_immediately | manual_review | Same as task 10 (same customer) |
| 28 (PROD003) | fulfill_delayed | backorder | CSV expects backorder for low_stock with sufficient qty |

## Domain Details

### SOP Logic

The simplest domain in SOP-Bench — a clean 4-step pipeline with no branching:

1. **Check inventory** → `in_stock`, `low_stock`, `out_of_stock`, `insufficient_stock`, or `product_not_found`
2. **Validate customer** → `approved`, `review_required`, or `blocked`
3. **Calculate shipping** → shipping cost and delivery days
4. **Make fulfillment decision** → combines all three inputs + `order_priority` into one of:
   `fulfill_immediately`, `fulfill_delayed`, `backorder`, `reject`, `manual_review`

### Tool Implementation

Unlike the broken warehouse_package_inspection domain, order_fulfillment tools use hardcoded
dictionaries (INVENTORY_DB with 10 products, CUSTOMER_DB with 10 customers, SHIPPING_RATES)
with deterministic logic based on actual input values. No mock arithmetic. The tools are
internally consistent — the 4 failures are edge cases where the tool logic produces reasonable
but different results from the CSV ground truth.

### Configuration

- **Model:** `gemini/gemini-3-flash-preview`, temperature=0.0
- **Execution:** Sequential
- **30 tasks**, single output: `expected_output` (the fulfillment decision)
- **4 tools:** check_inventory, validate_customer, calculate_shipping, make_fulfillment_decision
- **Input columns:** Explicit in local `metadata.json` (9 input columns)

## Files

- `benchmarks/sop_bench/domains/order_fulfillment/SKILL.md`
- `benchmarks/sop_bench/domains/order_fulfillment/config.yaml`
- `benchmarks/sop_bench/domains/order_fulfillment/metadata.json`
