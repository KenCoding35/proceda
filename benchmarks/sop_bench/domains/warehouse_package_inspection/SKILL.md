---
name: warehouse-package-inspection
description: Identifies, classifies, and resolves problematic shipment receipts through barcode validation, quantity variance analysis, location verification, and damage assessment.
required_tools:
  - validateBarcode
  - calculateQuantityVariance
  - verifyWarehouseLocation
  - assessPackageCondition
  - calculateChargeback
  - updateResolutionStatus
  - generateProblemReport
output_fields:
  - resolution_status
---

### Step 1: Validate Product Barcode
Execute the barcode validation protocol by calling `validateBarcode` with the `po_number`, `confirmed_product_id`, and `received_product_bar_code` (file path to the barcode image). If `barcode_match` is `False`, the product is a "Wrong Item" — set `resolution_status` to "Returned to Vendor" and skip directly to Step 7 (Problem Classification Report) with `problem_type` set to `["Wrong Item"]`. If the barcode matches, proceed to Step 2.

### Step 2: Calculate Quantity Variance
Call `calculateQuantityVariance` with `po_number`, `ordered_quantity`, `confirmed_quantity`, `received_quantity`, and `QVT` (Quantity Variance Threshold, default 5.0 if not provided). Record the returned `quantity_variance`, `problem_type` list, and `chargeable` status. The tool classifies quantity discrepancies: "Cancelled Quantity" (confirmed_quantity=0), "Overage Quantity" (received > ordered), "Underage Quantity" (received < ordered), and "Severe Unmatched Quantity" (variance exceeds QVT).

### Step 3: Verify Warehouse Location
Call `verifyWarehouseLocation` with `po_number`, `intended_warehouse_id`, and `actual_warehouse_id`. If `location_match` is `False`, add "Wrong Warehouse" to the accumulated `problem_type` list.

### Step 4: Assess Package Condition
Call `assessPackageCondition` with `po_number` and `package_image_path`. If `package_condition` is "damaged", add "Vendor Damaged" to the accumulated `problem_type` list.

### Step 5: Calculate Chargeback
Call `calculateChargeback` with `po_number`, the accumulated `problem_type` list, `ordered_quantity`, `received_quantity`, and `unit_cost`. Record the `chargeable` status and `charge_amount`.

### Step 6: Update Resolution Status
First check the accumulated `problem_type` list. If no problems were found (the list is empty), set `resolution_status` to "Resolved" and skip calling the tool. Otherwise, call `updateResolutionStatus` with `po_number`, the accumulated `problem_type` list, and `current_status` set to "Pending", and use the returned `resolution_status`.

### Step 7: Generate Problem Classification Report
Call `generateProblemReport` with `po_number`, `vendor_id`, `vendor_name`, the accumulated `problem_type` list, `charge_amount` (from Step 5, or 0.0 if skipped due to Wrong Item), and `resolution_status`. Output the final `resolution_status` value.
