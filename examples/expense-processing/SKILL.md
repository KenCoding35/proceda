---
name: expense-processing
description: Process expense reports with policy validation and approval checkpoints
required_tools:
  - receipts__extract
  - policy__validate
  - erp__submit
---

### Step 1: Extract receipt data
Use the receipts tool to extract all available receipt fields from the submitted expense report.

Look for:
- Date of purchase
- Vendor name
- Amount and currency
- Category (meals, travel, supplies, etc.)
- Payment method

### Step 2: Validate policy
[APPROVAL REQUIRED]
Check the extracted data against company policy and summarize any violations.

Policy rules to check:
- Single meal expense must not exceed $75
- Travel expenses require manager pre-approval
- Receipts older than 90 days are not reimbursable
- Entertainment expenses require attendee list

### Step 3: Submit to ERP
[PRE-APPROVAL REQUIRED]
Submit the approved expense report to the ERP system.

Include all validated receipt data and any policy notes in the submission.
