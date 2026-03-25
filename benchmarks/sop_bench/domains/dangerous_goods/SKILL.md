---
name: dangerous-goods
description: Establishes a standardized methodology for the systematic identification and classification of dangerous goods hazard classes through multi-source data integration and quantitative severity assessment.
required_tools:
  - calculate_sds_label_score
  - calculate_handling_score
  - calculate_transportation_score
  - calculate_disposal_score
---

### Step 1: Validate Product Identification Data
Verify product identification documentation completeness using the Document Validation Protocol (DVP-2023). Cross-reference the `product_id` against the master dangerous goods database. If the `product_id` fails to meet format requirements (e.g., missing prefix, invalid character set, or non-resolvable reference), set `hazard_score` to 0 and `hazard_class` to "Unable to Decide", then terminate the procedure.

### Step 2: Calculate Safety Data Sheet Score
Extract hazard statements from Section 2 of the Safety Data Sheet (SDS). Use the `calculate_sds_label_score` tool to determine the `safety_score` for the `product_id` based on the `sds_label_text`. Validate that the `safety_score` is between 1 and 5.

### Step 3: Calculate Handling and Storage Score
Parse the provided Handling and Storage Guidelines. Use the `calculate_handling_score` tool to determine the `handling_score` for the `product_id` based on `handling_and_storage_guidelines`. Validate that the `handling_score` is between 1 and 5.

### Step 4: Calculate Transportation Severity Score
Analyze the Transportation Requirements. Use the `calculate_transportation_score` tool to obtain the `transportation_score` for the `product_id` based on `transportation_requirements`. Validate that the `transportation_score` is between 1 and 5.

### Step 5: Calculate Disposal Severity Score
Process the Disposal Guidelines. Use the `calculate_disposal_score` tool to calculate the `disposal_score` for the `product_id` based on `disposal_guidelines`. Validate that the `disposal_score` is between 1 and 5.

### Step 6: Compute Cumulative Hazard Score
If any individual score (safety_score, handling_score, transportation_score, disposal_score) is missing or 0, impute it by taking the maximum of the available scores. If more than two component scores are missing, set `hazard_score` to 0 and `hazard_class` to "Unable to Decide", then terminate the procedure. Calculate `hazard_score` = `safety_score` + `handling_score` + `transportation_score` + `disposal_score`. Validate that the `hazard_score` is within the acceptable range of 4-20.

### Step 7: Determine and Document Hazard Class
Based on the `hazard_score`, determine the `hazard_class` (A, B, C, or D), where a higher score indicates higher severity (D being the highest). Document the final `hazard_class` designation and `hazard_score` in the Hazard Classification Registry. Output the final classification in XML format with tags `<hazard_score>` and `<hazard_class>`.