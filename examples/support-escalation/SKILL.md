---
name: support-escalation
description: Triage and escalate customer support tickets based on severity and impact
required_tools:
  - tickets__get
  - tickets__update
  - notifications__send
---

### Step 1: Retrieve ticket details
Use the tickets tool to fetch the full ticket details including customer history, priority level, and any previous interactions.

### Step 2: Assess severity
Analyze the ticket content and determine the severity level:
- P1 (Critical): Service outage affecting multiple customers
- P2 (High): Major feature broken for a single customer
- P3 (Medium): Non-critical issue with workaround available
- P4 (Low): Feature request or minor cosmetic issue

### Step 3: Route and escalate
[APPROVAL REQUIRED]
Based on the severity assessment:
- P1/P2: Escalate to on-call engineering team
- P3: Assign to support queue
- P4: Add to backlog

Update the ticket with the routing decision and notify relevant parties.

### Step 4: Confirm notification
Verify that all notifications were sent successfully and the ticket status is updated.
