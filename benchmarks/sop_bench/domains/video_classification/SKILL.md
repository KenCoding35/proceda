---
name: video-classification
description: Establishes a multi-tiered review system for classifying, escalating, and moderating user-generated video content.
required_tools:
  - validateVideo
  - checkUserHistory
  - assignReviewer
  - getReview
  - submitContentModeration
  - detectHateSpeech
  - detectExplicitContent
  - implementModeration
  - assessAgeRating
  - generateContentWarnings
output_fields:
  - final_decision
---

### Step 1: Validate Video Content and Uploader History
Execute the Video Validation Protocol (VVP) to validate video format compliance against supported codec specifications (MP4, HEVC/H.264) and ensure a minimum resolution of 720p. Account for typos in specifications and do not discard based on them. Perform metadata extraction and validation according to the platform's Metadata Extraction Protocol (MEP).
Call the `validateVideo` tool with `video_id` and `video_path`.
Perform an analysis to ensure the uploader's history is clean; otherwise, identify red flags and exercise caution.
Call the `checkUserHistory` tool with `uploader_id`.
If video validation and uploader history analysis are positive, proceed to the next stage of the moderation process.

### Step 2: Assign Initial Reviewer
Run the Reviewer Assignment Algorithm (RAA) incorporating reviewer expertise metrics, language proficiency scores, and current workload distribution factors. Assign an `initial_reviewer_id` based on optimal reviewer selection criteria.
Call the `assignReviewer` tool with `video_id`, `video_language`, and `region`.
Based on the initial reviewer's detected categories and their confidences, decide if the content needs to be escalated to a moderation expert.

### Step 3: Conduct Initial Content Review
Execute the Review Session Protocol (RSP), including mandatory full-length video review and documentation requirements.
Call the `getReview` tool with `video_id` and `initial_reviewer_id` to fetch the review details.
Apply the Content Classification Taxonomy (CCT) to identify and classify content violations.
Calculate `confidence_scores` for each identified violation category.
Return empty fields if no categories and confidence scores are detected.

### Step 4: Process Content Classification and Generate Report
Apply classification algorithms to `detected_categories` based on review findings.
Call the `detectHateSpeech` tool with `video_id` and `transcript` (assuming transcript is available).
Call the `detectExplicitContent` tool with `video_id`.
Calculate a composite violation severity score using weighted category metrics.
Generate a preliminary classification report including violation details and confidence scores.
Call the `submitContentModeration` tool with `video_id` and `initial_reviewer_id`.
[APPROVAL REQUIRED]

### Step 5: Determine Escalation Requirements
Calculate the Escalation Threshold Metric (ETM) based on the violation severity and confidence scores from the preliminary classification report.
Compare the ETM against established escalation thresholds.
If the ETM exceeds the threshold, initiate the escalation protocol and assign a `moderator_id`.
Document the escalation justification and associated metrics.

### Step 6: Implement Moderation Actions
Generate comprehensive `moderator_notes` documenting timestamps and descriptions of potentially objectionable content.
Apply the Moderation Action Matrix (MAM) to determine appropriate actions and embed them in your notes.
Upload the data to the database as per data upload guidelines within 24 hours of the case being assigned.
Call the `implementModeration` tool with `video_id` and `moderator_id` (if assigned in Step 5).
[APPROVAL REQUIRED]

### Step 7: Final Review, Documentation, and Decision
Generate comprehensive review documentation including all decision points and justifications.
If the content was escalated, go through the moderator's detailed notes to identify potential moderation actions: Age Restrict, Remove, Strike Issued, Warning. You may issue one or more actions as per the case or None.
Assign an age rating based on the reviewers' input and moderation actions.
Call the `assessAgeRating` tool with `video_id` and `content_flags` (derived from detected issues and moderation actions) to determine the age rating ('18+', '13+', or None).
Assign a content warning (True or False) based on all signals.
Call the `generateContentWarnings` tool with `video_id` and `detected_issues` (derived from detected issues and moderation actions).
Based on all signals, including technical issues with the video or inappropriate content flagged by reviewers and moderators, assign a `final_decision` from these options: Remove, Warning, Allow, Age Restrict. Note that allowed content may or may not have a content warning status as True, and technical hiccups in content may result in a Remove decision.
Archive review session data according to data retention policies.
[APPROVAL REQUIRED]
Complete the step by providing the final decision.
<final_decision>value</final_decision>