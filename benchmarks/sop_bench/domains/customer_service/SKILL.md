---
name: customer-service
description: Diagnoses and resolves customer-reported service issues without interactive communication, using system logs and internal tools.
required_tools:
  - validateAccount
  - getAuthenticationDetails
  - createSessionAndOpenTicket
  - checkAccountStatus
  - checkPaymentStatus
  - checkAccountSuspensionStatus
  - checkServiceAreaOutage
  - performTechnicalDiagnostics
  - executeTroubleshooting
  - createEscalation
---

### Step 1: Validate Account ID Format
Validate the format of the provided `account_id` to ensure it conforms to the organization's standard pattern (e.g., ABC-12345). If the format is invalid, log the issue and immediately terminate the process.
- Call: `validateAccount(account_id: "<customer_account_id>")`

### Step 2: Retrieve Authentication History
If the `account_id` is valid, retrieve the customer's most recent authentication history. If a failed attempt is found with no record of successful recovery, classify the authentication as failed and close the case.
- Call: `getAuthenticationDetails(account_id: "<customer_account_id>", is_account_id_valid: <boolean_from_step_1>)`

### Step 3: Initialize Service Ticket
If the customer meets authentication requirements, generate a unique session token and open a new service ticket. Record both the session token and ticket ID, and use them throughout the remainder of the workflow.
- Call: `createSessionAndOpenTicket(account_id: "<customer_account_id>", is_account_id_valid: <boolean_from_step_1>, is_authenticated: <boolean_from_step_2>)`

### Step 4: Evaluate Current Account Status
Query the system to determine the current status of the customer's account. If the system flags the account as *Terminated*, log the termination reason and conclude the case, as the account is ineligible for support. If the account is *Active*, record this status and proceed.
- Call: `checkAccountStatus(account_id: "<customer_account_id>", session_token: "<session_token_from_step_3>")`

### Step 5: Check Account Suspension for Non-Payment [OPTIONAL]
If the account is *Suspended* due to non-payment, verify the payment status. If the payment has been made and the suspension lifted, continue with the workflow. Otherwise, assign the case to the Accounts Payable department or conclude if ineligible for support.
- Call: `checkPaymentStatus(account_id: "<customer_account_id>", session_token: "<session_token_from_step_3>")`

### Step 6: Verify Account Suspension Status [OPTIONAL]
If the account was *Suspended* for reasons other than non-payment, or if a previous suspension should now be lifted, verify the current suspension status. If the suspension has been lifted, continue with the workflow.
- Call: `checkAccountSuspensionStatus(account_id: "<customer_account_id>", session_token: "<session_token_from_step_3>")`

### Step 7: Analyze Service Area for Outages
Access the outage monitoring system and search for recent or ongoing service disruptions within a 10-mile radius of the customer's service address. If an outage is detected, log the outage ID, impact scope, and estimated resolution time, then conclude diagnostics as the root cause is known.
- Call: `checkServiceAreaOutage(account_id: "<customer_account_id>", session_token: "<session_token_from_step_3>", service_area_code: "<customer_service_area_code>")`

### Step 8: Perform Technical Diagnostics
If no outage exists, select and run the appropriate diagnostic tools based on the customer's service type (e.g., internet, voice, video). Measure key performance indicators, including latency, jitter, and bandwidth throughput. Evaluate each metric against defined thresholds and identify potential root causes. Record all diagnostic values, interpretations, and inferred causes.
- Call: `performTechnicalDiagnostics(account_id: "<customer_account_id>", session_token: "<session_token_from_step_3>", service_type: "<customer_service_type>", subscribed_bandwidth: "<customer_subscribed_bandwidth>")`

### Step 9: Execute Troubleshooting Steps
Run all appropriate resolution steps using predefined troubleshooting guidelines (e.g., modem resets, signal refreshes, provisioning adjustments) based on the identified root causes. After troubleshooting, re-execute diagnostics to assess changes in latency, jitter, and bandwidth. If metrics improve, classify the issue as fixed.
- Call: `executeTroubleshooting(account_id: "<customer_account_id>", session_token: "<session_token_from_step_3>", root_causes: ["<root_cause_1>", "<root_cause_2>"])`

### Step 10: Create Escalation Ticket [OPTIONAL]
If automated troubleshooting fails to resolve the issue (i.e., no significant improvement in metrics), determine the appropriate escalation path. Create a new escalation ticket, link it to the primary case, and include all relevant diagnostic outputs, attempted troubleshooting steps, and a summary of findings. Assign the ticket to the appropriate support group (Tier 2 Technical Support, Field Operations, or Network Engineering).
- Call: `createEscalation(session_token: "<session_token_from_step_3>", ticket_id: "<ticket_id_from_step_3>", metrics_improved_post_troubleshooting: <boolean_from_step_9_re_diagnostics>, escalation_required: <boolean_based_on_troubleshooting_outcome>)`

### Step 11: Document Final Resolution
Compile a comprehensive resolution summary including customer account details, authentication results, service status, diagnostic data, troubleshooting actions, and any escalations performed, along with relevant timestamps. Update the ticket with the final resolution status: `RESOLVED`, `PENDING_ACTION`, `ESCALATED`, or `FAILED`.