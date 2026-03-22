---
name: customer-service
description: Diagnoses and resolves customer-reported service issues offline using system logs and internal tools, ensuring end-to-end consistency and traceability.
required_tools:
  - validateAccount
  - getAuthenticationDetails
  - createSessionAndOpenTicket
  - checkAccountStatus
  - checkServiceAreaOutage
  - performTechnicalDiagnostics
  - executeTroubleshooting
  - checkPaymentStatus
  - createEscalation
  - checkAccountSuspensionStatus
output_fields:
  - final_resolution_status
---

### Step 1: Validate Account ID Format
Validate the format of the provided `Account ID`. If the format is invalid, log the issue and immediately terminate the process.
`validateAccount(account_id={{account_id}})`

### Step 2: Retrieve Authentication History
Retrieve the customer's most recent authentication history. If you find failed attempts and no record of successful recovery, classify the authentication as failed and close the case.
`getAuthenticationDetails(account_id={{account_id}}, is_account_id_valid={{is_account_id_valid}})`

### Step 3: Create Session and Open Service Ticket
If the customer meets the authentication requirements, generate a unique session token and open a new service ticket. Record both the session token and ticket ID, and use them throughout the remainder of the workflow.
`createSessionAndOpenTicket(account_id={{account_id}}, is_account_id_valid={{is_account_id_valid}}, is_authenticated={{is_authenticated}})`

### Step 4: Evaluate Account Status
Query the system to determine the current status of the customer's account. If the system flags the account as `Terminated`, log the termination reason and conclude the case, as the account is ineligible for support.
If the account is `Suspended`, extract the specific reason for suspension. If the cause relates to non-payment, assign the case to the Accounts Payable department, and then use `checkPaymentStatus(account_id={{account_id}}, session_token={{session_token}})` to verify payment status. If the reason is something else, conclude the case, as the account is ineligible for support. Post suspension resolution steps, if the system shows that the suspension has been lifted, use `checkAccountSuspensionStatus(account_id={{account_id}}, session_token={{session_token}})` to confirm and continue with the workflow.
If the account status is `Active`, record this status and proceed to the next step.
`checkAccountStatus(account_id={{account_id}}, session_token={{session_token}})`

### Step 5: Analyze for Outages in Service Area
Access the outage monitoring system and search for recent or ongoing service disruptions within a 10-mile radius of the customer's service address. If you detect an outage, log the outage ID, impact scope, and estimated resolution time. You may conclude diagnostics at this point, as the root cause is known. If no outage exists, continue to the technical diagnostic phase.
`checkServiceAreaOutage(account_id={{account_id}}, session_token={{session_token}}, service_area_code={{derive_service_area_code_from_account_id_or_customer_details}})`

### Step 6: Perform Technical Diagnosis
Select and run the appropriate diagnostic tools based on the type of service the customer uses (e.g., internet, voice, video). Measure key performance indicators, including latency, jitter, and bandwidth throughput. Evaluate each metric against defined thresholds. Flag latency values exceeding 100 milliseconds, jitter over 30 milliseconds, or bandwidth levels that fall below the customer's subscribed plan. Use the diagnostic results and any relevant account history to identify potential root causes. Rank these causes by their likelihood and relevance. Record all diagnostic values, interpretations, and inferred causes in the service ticket, including precise timestamps for traceability.
`performTechnicalDiagnostics(account_id={{account_id}}, session_token={{session_token}}, service_type={{derive_service_type_from_account_details}}, subscribed_bandwidth={{derive_subscribed_bandwidth_from_account_details}})`

### Step 7: Execute Troubleshooting Steps
Run all appropriate resolution steps using predefined troubleshooting guidelines, such as modem resets, signal refreshes, or provisioning adjustments based on the identified root causes.
`executeTroubleshooting(account_id={{account_id}}, session_token={{session_token}}, root_causes={{root_cause_list_from_diagnostics}})`

### Step 8: Re-evaluate Diagnostics Post-Troubleshooting
After troubleshooting is complete, re-execute diagnostics to assess changes in latency, jitter, and bandwidth. If metrics improve, classify the issue as fixed. If you observe no significant improvement after executing all troubleshooting steps, proceed to the escalation phase.
`performTechnicalDiagnostics(account_id={{account_id}}, session_token={{session_token}}, service_type={{derive_service_type_from_account_details}}, subscribed_bandwidth={{derive_subscribed_bandwidth_from_account_details}})`

### Step 9: Escalate Unresolved Issues
If automated troubleshooting fails to resolve the issue, determine the appropriate escalation path based on the nature of the problem. Create a new escalation ticket and link it to the primary case. Include all relevant diagnostic outputs, attempted troubleshooting steps, customer and device information, and a summary of findings. Assign the ticket to the appropriate support group: Tier 2 Technical Support for complex diagnostic scenarios, Field Operations team for on-site issues, and Network Engineering for infrastructure problems. Log the escalation destination, reason, and service-level expectations.
`createEscalation(session_token={{session_token}}, ticket_id={{ticket_id}}, metrics_improved_post_troubleshooting={{metrics_improved_after_troubleshooting}}, escalation_required=True)`

### Step 10: Document Final Resolution Status
Compile a comprehensive resolution summary. Include customer account details, authentication results, service status, diagnostic data, troubleshooting actions, and any escalations performed, along with relevant timestamps. Then, update the ticket with the final resolution status: mark it as `RESOLVED` if the issue was addressed, `PENDING_ACTION` if the issue is awaiting a dependent action (e.g., outage resolution), `ESCALATED` if the initial diagnosis and troubleshooting could not resolve the issue and it is therefore assigned to another expert team, or `FAILED` if authentication was not completed.
<final_resolution_status>{{final_resolution_status_value}}</final_resolution_status>