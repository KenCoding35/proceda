---
name: content-flagging
description: Establishes a comprehensive framework for evaluating, classifying, and disposing of flagged content within the platform's content moderation ecosystem.
required_tools:
  - calculateBotProbabilityIndex
  - calculate_user_trust_score
  - calculateContentSeverityIndex
  - determineFinalDecision
---

### Step 1: Calculate Bot Probability Index
Utilize the `calculateBotProbabilityIndex` tool to assess the likelihood of automated activity, incorporating device consistency validation.
This tool will take the following inputs:
- `userid` from content metadata
- `is_possible_bot` (initial bot assessment)
- `Captcha_tries` (number of captcha attempts)
- `device_type` from device information
- `os` (operating system) from device information
- `browser` (browser specification) from device information
The outputs will be the `bot_probability_index` and the `device_consistency_score`.

### Step 2: Calculate User Trust Score
Compute the user's overall trust coefficient using the `calculate_user_trust_score` tool, factoring in historical behavior, geographic risk, and device consistency.
This tool requires:
- `userid` from content metadata
- `NumberofPreviousPosts` (user's total post count)
- `CountofFlaggedPosts` (count of user's previously flagged posts)
- `Latitude` and `Longitude` from content metadata (geolocation coordinates)
- `bot_probability_index` obtained from Step 1
- `device_consistency_score` obtained from Step 1
The output will be the `user_trust_score`.

### Step 3: Assess Content Severity
Determine the severity of the content violation using the `calculateContentSeverityIndex` tool, integrating primary and secondary violation analyses.
Provide the following inputs:
- `content_id` from content metadata
- `PrimaryViolationType` from violation data
- `SecondaryViolationType` from violation data (if applicable)
- `PrimaryViolation_Confidence` from violation data
- `SecondaryViolation_Confidence` from violation data (if applicable)
The output will be the `content_severity_index`.

### Step 4: Determine Final Content Disposition
Utilize the `determineFinalDecision` tool to combine all moderation metrics and establish the final action for the flagged content.
This tool needs:
- `content_id` from content metadata
- `user_trust_score` obtained from Step 2
- `content_severity_index` obtained from Step 3
- `bot_probability_index` obtained from Step 1
- `NumberofPreviousPosts` (user's total post count)
- `CountofFlaggedPosts` (count of user's previously flagged posts)
The tool will output the final disposition (e.g., `removed`, `warning`, `user_banned`, `allowed`).
[APPROVAL REQUIRED]