---
name: traffic-spoofing-detection
description: Detects and investigates affiliate marketing traffic spoofing violations to determine enforcement actions.
required_tools:
  - InvestigateViolations
  - AnalyzeTrafficPatterns
  - ValidateReferralSources
  - CalculateRiskScore
  - GenerateEvidenceReport
  - ExecuteEnforcementAction
output_fields:
  - enforcement_action
---

### Step 1: Validate Partner Account
Execute the Traffic Attribution Validation Matrix (TAVM) by calling the `InvestigateViolations` tool. Use the `partner_id`, `registered_websites`, and `earnings_amount`. Cross-reference the earnings against violation thresholds and ensure the ratio of `unique_users` to `total_orders` is at least 0.4.

### Step 2: Analyze Traffic Patterns
Analyze engagement and conversion metrics by calling the `AnalyzeTrafficPatterns` tool. Provide the `partner_id`, `engagement_score`, `conversion_rate`, and `bounce_rate`. Identify critical engagement (<1.0), suspicious conversion rates (<0.05%), and document any `click_spike` exceeding 10x the baseline or device traffic distribution exceeding 80% for a single type.

### Step 3: Authenticate Traffic Sources
Verify the legitimacy of referral sources by calling the `ValidateReferralSources` tool. Use the `partner_id`, `unattributed_clicks`, and `top_referral_source`. Flag the traffic as suspicious if `unattributed_clicks` exceed 50%, `bounce_rate` is over 90%, or `visit_duration_seconds` is under 30 seconds.

### Step 4: Classify Violation and Calculate Risk
Determine the violation category (Traffic Cloaking, Spoofing Traffic, Redirect Traffic, or Blank Source) and calculate the severity by calling the `CalculateRiskScore` tool. Use the `partner_id`, the identified `violation_type`, `engagement_score`, and `conversion_rate`.

### Step 5: Document Evidence
[APPROVAL REQUIRED]
Generate a formal evidence report for the Partner Violation Documentation System (PVDS) by calling the `GenerateEvidenceReport` tool. Include the `partner_id`, `violation_type`, and a detailed list of `evidence_collected` from the previous analysis steps.

### Step 6: Determine and Execute Enforcement Action
[APPROVAL REQUIRED]
Execute the final enforcement action based on the calculated risk level and violation type by calling the `ExecuteEnforcementAction` tool. Use the `partner_id`, `risk_level`, and `violation_type`.
- High Risk: Account Closure
- Medium Risk: Temporary Suspension
- Low Risk (with evidence): Warning Issued
- Low Risk (no evidence): No Action

Include the final determination in the summary using the XML tag: <enforcement_action>value</enforcement_action>