---
name: referral-abuse-detection-v2
description: Detects referral abuse violations with temporal pattern analysis and risk-severity-based enforcement actions.
required_tools:
  - investigate_account
  - analyze_traffic_patterns
  - analyze_temporal_patterns
  - get_violation_history
  - get_financial_impact
  - determine_enforcement_action
output_fields:
  - final_decision
---

### Step 1: Investigate Account
Call `investigate_account` with `account_id`. Record all returned fields: `address_validity`, `email_pattern_suspicious`, `website_verified`, `business_description`, `account_status`, `connected_accounts`, `login_geographic_consistency`, and `account_age_days`.

### Step 2: Analyze Traffic Patterns
Call `analyze_traffic_patterns` with `account_id`. Record all returned fields: `revenue_amount`, `click_through_rate`, `page_views`, `device_distribution`, `referral_source_quality`, `payment_method_shared`, and `order_patterns_suspicious`.

### Step 3: Analyze Temporal Patterns
Call `analyze_temporal_patterns` with `account_id`. Record all returned fields: `registration_burst_detected`, `off_hours_activity_percentage`, and `activity_spike_detected`.

### Step 4: Get Violation History
Call `get_violation_history` with `account_id`. Record all returned fields: `previous_violations_count`, `last_violation_date`, `warning_issued`, and `account_rehabilitation_status`.

### Step 5: Get Financial Impact
Call `get_financial_impact` with `account_id`. Record all returned fields: `total_lifetime_revenue`, `refund_rate_percentage`, and `customer_complaint_count`.

### Step 6: Get Enforcement Guidelines
Call `determine_enforcement_action` with `account_id` to retrieve enforcement action guidelines.

### Step 7: Calculate Violation Scores, Risk Severity, and Determine Enforcement Action

Using data from Steps 1-5, calculate five violation scores. Note: some indicators are WEIGHTED (worth +2 instead of +1).

**Abusive Account Creation Score** (threshold >= 4):
- address_validity is false (+1)
- email_pattern_suspicious is true (+1)
- website_verified is false (+1)
- connected_accounts >= 15 (+1)
- login_geographic_consistency is false (+1)
- registration_burst_detected is true (+2) [WEIGHTED]
- account_age_days < 30 (+1)

**Misleading Ad Copy Score** (threshold >= 4):
- website_verified is false (+1)
- referral_source_quality is "Low" or "Medium" (+1)
- order_patterns_suspicious is true (+1)
- click_through_rate > 0.4 (+1)
- activity_spike_detected is true (+1)
- customer_complaint_count > 5 (+1)

**Personal Orders Score** (threshold >= 3):
- payment_method_shared is true (+1)
- connected_accounts > 0 AND connected_accounts < 15 (+1)
- order_patterns_suspicious is true (+1)
- referral_source_quality is "High" (+1)
- off_hours_activity_percentage < 30 (+1)

**Temporal Fraud Score** (threshold >= 4):
- registration_burst_detected is true (+2) [WEIGHTED]
- off_hours_activity_percentage > 60 (+1)
- activity_spike_detected is true (+1)
- account_age_days < 30 AND connected_accounts >= 15 (+2) [WEIGHTED]

**No Violation Score** (threshold >= 6):
- address_validity is true (+1)
- email_pattern_suspicious is false (+1)
- website_verified is true (+1)
- login_geographic_consistency is true (+1)
- payment_method_shared is false (+1)
- order_patterns_suspicious is false (+1)
- registration_burst_detected is false (+1)
- off_hours_activity_percentage < 30 (+1)
- customer_complaint_count <= 2 (+1)

**Determine violation type:** Choose the category with the HIGHEST score that meets its threshold. If multiple meet threshold, choose the highest score. If tied, use priority: Temporal Fraud > Abusive Account Creation > Misleading Ad Copy > Personal Orders. If no score meets any threshold, the result is INCONCLUSIVE.

**Calculate Risk Severity** (for violations only, not No Violation or Inconclusive):

CRITICAL if ANY: revenue_amount > 5000, OR previous_violations_count >= 2, OR (previous_violations_count >= 1 AND warning_issued is true AND last_violation_date within 90 days), OR customer_complaint_count > 10.

HIGH if ANY: (revenue_amount > 1000 AND revenue_amount <= 5000), OR previous_violations_count == 1, OR connected_accounts >= 25, OR refund_rate_percentage > 40.

MEDIUM if ANY: (revenue_amount > 100 AND revenue_amount <= 1000), OR account_rehabilitation_status is "Probation", OR (connected_accounts >= 15 AND connected_accounts < 25).

LOW: All other violation cases.

**Apply enforcement action** based on violation type AND risk severity:

For Abusive Account Creation, Misleading Ad Copy, or Temporal Fraud:
- CRITICAL → "Permanent Account Closure"
- HIGH → "Account Closure"
- MEDIUM → "Temporary Suspension"
- LOW → "Warning Issued"

For Personal Orders (Related):
- CRITICAL → "Account Closure"
- HIGH → "Temporary Suspension"
- MEDIUM → "Warning Issued"
- LOW → "No Action"

For No Violation → "No Action"

For INCONCLUSIVE:
- If previous_violations_count > 0 → "Manual Review Required"
- Otherwise → "Inconclusive"
