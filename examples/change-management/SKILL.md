---
name: change-management
description: Manage infrastructure change requests with review and approval gates
required_tools:
  - infra__plan
  - infra__apply
  - monitoring__check
---

### Step 1: Review change request
Review the submitted change request and verify it includes:
- Description of the change
- Impact assessment
- Rollback plan
- Maintenance window (if applicable)

### Step 2: Generate infrastructure plan
[PRE-APPROVAL REQUIRED]
Use the infra tool to generate a plan for the proposed changes. Present the plan details including:
- Resources to be created, modified, or destroyed
- Estimated impact and downtime
- Dependencies

### Step 3: Apply changes
[PRE-APPROVAL REQUIRED]
Apply the approved infrastructure changes using the infra tool.

Monitor the apply process and report any errors immediately.

### Step 4: Verify deployment
Use the monitoring tool to verify the changes were applied successfully:
- Check service health endpoints
- Verify metrics are within normal ranges
- Confirm no new alerts have been triggered

### Step 5: Close change request
[OPTIONAL]
Update the change request with the results and close it.

Include a summary of:
- What was changed
- Any issues encountered
- Verification results
