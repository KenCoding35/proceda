---
name: referral-abuse-detection-v2
description: Detects and investigates referral abuse violations to determine risk severity and appropriate enforcement actions.
required_tools:
  - investigate_account
  - analyze_temporal_patterns
  - analyze_traffic_patterns
  - get_violation_history
  - get_financial_impact
  - determine_enforcement_action
output_fields:
  - final_decision
---

### Step 1: Investigate Account Details
Call the `investigate_account` tool using the `account_id` parameter to retrieve account investigation data. Review the user's account, promotional websites, address validity, email authenticity, business description, account status, and account age. 

### Step 2: Analyze Temporal Patterns
Call the `analyze_temporal_patterns` tool using the `account_id` parameter to retrieve temporal activity data. Analyze registration timing for coordinated creation, review off-hours activity percentage, detect unusual traffic surges, and cross-reference registration timestamps with connected accounts.

### Step 3: Analyze Traffic and Relations
Call the `analyze_traffic_patterns` tool using the `account_id` parameter to retrieve traffic and transaction data. Review key metrics (revenue patterns, click-through rates, page views, device distribution), conduct URL analysis, and perform relationship analysis (connected accounts, shared payment methods).

### Step 4: Retrieve Violation History
Call the `get_violation_history` tool using the `account_id` parameter to retrieve detailed violation history. Review the previous violations count, last violation date, warning status, and rehabilitation status.

### Step 5: Determine Financial Impact
Call the `get_financial_impact` tool using the `account_id` parameter to retrieve financial metrics. Assess the total lifetime revenue, refund rate percentage, and customer complaint count.

### Step 6: Document Investigation Findings
[OPTIONAL]
Gather evidence such as screenshots, screen recordings, URLs, and any other relevant information to support the findings. Make a ticket if the total earnings on the account meet thresholds or if the enforcement action may attract Legal, PR, or Brand Safety concerns.

### Step 7: Calculate Violation Indicators and Determine Violation Type
Calculate scores based on the gathered data by counting TRUE indicators (ensure boolean values are compared as true/false):

1. Abusive Account Creation Score:
- address_validity is false (+1)
- email_pattern_suspicious is true (+1)
- website_verified is false (+1)
- connected_accounts >= 15 (+1)
- login_geographic_consistency is false (+1)
- registration_burst_detected is true (+2)
- account_age_days < 30 (+1)
(Score >= 4 → Abusive Account Creation)

2. Misleading Ad Copy Score:
- website_verified is false (+1)
- referral_source_quality is "Low" or "Medium" (+1)
- order_patterns_suspicious is true (+1)
- click_through_rate > 0.4 (+1)
- activity_spike_detected is true (+1)
- customer_complaint_count > 5 (+1)
(Score >= 4 → Misleading Ad Copy)

3. Personal Orders Score:
- payment_method_shared is true (+1)
- connected_accounts > 0 AND connected_accounts < 15 (+1)
- order_patterns_suspicious is true (+1)
- referral_source_quality is "High" (+1)
- off_hours_activity_percentage < 30 (+1)
(Score >= 3 → Personal Orders (Related))

4. Temporal Fraud Score:
- registration_burst_detected is true (+2)
- off_hours_activity_percentage > 60 (+1)
- activity_spike_detected is true (+1)
- account_age_days < 30 AND connected_accounts >= 15 (+2)
(Score >= 4 → Temporal Fraud Pattern)

5. No Violation Score:
- address_validity is true (+1)
- email_pattern_suspicious is false (+1)
- website_verified is true (+1)
- login_geographic_consistency is true (+1)
- payment_method_shared is false (+1)
- order_patterns_suspicious is false (+1)
- registration_burst_detected is false (+1)
- off_hours_activity_percentage < 30 (+1)
- customer_complaint_count <= 2 (+1)
(Score >= 6 → No Violation)

Determine violation type based on HIGHEST score. If tied, use priority: Temporal Fraud > Abusive Account Creation > Misleading Ad Copy > Personal Orders. If no score meets its threshold, the result is INCONCLUSIVE.

### Step 8: Calculate Risk Severity Level
Calculate Risk Severity for violations (not applicable for "No Violation" or "Inconclusive"):

CRITICAL Risk if ANY of:
- revenue_amount > 5000
- previous_violations_count >= 2
- (previous_violations_count >= 1 AND warning_issued is true AND last_violation_date within 90 days)
- customer_complaint_count > 10

HIGH Risk if ANY of:
- revenue_amount > 1000 AND revenue_amount <= 5000
- previous_violations_count == 1
- connected_accounts >= 25
- refund_rate_percentage > 40

MEDIUM Risk if ANY of:
- revenue_amount > 100 AND revenue_amount <= 1000
- account_rehabilitation_status is "Probation"
- connected_accounts >= 15 AND connected_accounts < 25

LOW Risk:
- All other violation cases not meeting above criteria.

### Step 9: Determine Enforcement Action
Call the `determine_enforcement_action` tool using the `account_id` parameter, then apply the following enforcement matrix based on the violation type and risk severity:

For Abusive Account Creation or Misleading Ad Copy or Temporal Fraud:
- CRITICAL Risk → "Permanent Account Closure"
- HIGH Risk → "Account Closure"
- MEDIUM Risk → "Temporary Suspension"
- LOW Risk → "Warning Issued"

For Personal Orders (Related):
- CRITICAL Risk → "Account Closure"
- HIGH Risk → "Temporary Suspension"
- MEDIUM Risk → "Warning Issued"
- LOW Risk → "No Action"

For No Violation:
- Always → "No Action"

For INCONCLUSIVE:
- If previous_violations_count > 0 → "Manual Review Required"
- Otherwise → "Inconclusive"

[APPROVAL REQUIRED]

### Step 10: Output Final Decision
Output the final enforcement decision using the exact value determined in the previous step. Include the `final_decision` value in the complete_step summary using XML tags.

Example:
<final_decision>Permanent Account Closure</final_decision>