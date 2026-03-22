---
name: order-fulfillment
description: Processes customer orders through inventory check, customer validation, shipping calculation, and fulfillment decision.
required_tools:
  - check_inventory
  - validate_customer
  - calculate_shipping
  - make_fulfillment_decision
output_fields:
  - expected_output
---

### Step 1: Check Inventory Status
Call `check_inventory` with `product_id` and `quantity_requested`. Record the returned `inventory_status` (in_stock, low_stock, out_of_stock, insufficient_stock, or product_not_found) for use in Step 4.

### Step 2: Validate Customer Account
Call `validate_customer` with `customer_id` and `order_total`. Record the returned `customer_status` (approved, review_required, or blocked) for use in Step 4.

### Step 3: Calculate Shipping Cost
Call `calculate_shipping` with `destination_zip`, `package_weight`, and `shipping_speed`. Record the returned `shipping_cost` for use in Step 4.

### Step 4: Determine Fulfillment Decision
Call `make_fulfillment_decision` with `inventory_status` (from Step 1), `customer_status` (from Step 2), `shipping_cost` (from Step 3), and `order_priority`. The tool returns the final `decision` which is the `expected_output`: one of fulfill_immediately, fulfill_delayed, backorder, reject, or manual_review.
