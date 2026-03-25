---
name: know-your-business
description: Establishes a comprehensive framework for conducting systematic verification of business entities in accordance with regulatory requirements.
required_tools:
  - getBusinessProfile
  - verifyBusinessRegistration
  - getOwnershipData
  - verifyUBO
  - performSanctionsCheck
  - getBankData
  - verifyBankAccount
  - calculateRiskScore
output_fields:
  - escalation_status
---

### Step 1: Retrieve and Validate Business Profile
The verification specialist shall retrieve the complete business profile using the `business_id` as the primary key by calling the `getBusinessProfile` tool. Ensure all required fields are populated according to the data schema specifications. Validate the presence and format of `business_name`, `contact_info`, `website`, `address`, `email`, `registration_number`, and `tax_id` from the retrieved profile.
Business names are automatically validated when TIN or any other government based ID is entered in the system. Use your experience to check if the website and/or address and/or email matches with the pre-validated business name. Due to errors by associates, there may be typos. For webpages, there may be some omissions in the text. Make sure that addresses have street number, road and the city. If the business is in World Trade Center, NY or in a known building, they may omit the street number. Use your experience to identify if the errors are genuine typos by associates entering the data or made-up names submitted by the businesses. If you believe that there are some irregularities here, please set the status as 'awaiting information' so that associates can reach out to these businesses for additional data.
Call the tool: `getBusinessProfile(business_id=business_id)`

### Step 2: Assess Documentation Completeness
Conduct a systematic evaluation of submitted documentation, generating a `documentation_completeness` status for your notes. Documentation is considered "Complete" only when all required fields are populated and validated against prescribed format requirements.

### Step 3: Validate Business Registration and Licensing
Ensure that Tax IDs are TIN followed by 6 digits only and they cannot be the same digit. If so, escalate immediately. Do not be case sensitive. Check that the license is not expired for more than 42 days, else escalate the case. Use the `verifyBusinessRegistration` tool to access government portals to verify registration status, license expiry, and date of entry. Maintain a record of all verification attempts and results.
Call the tool: `verifyBusinessRegistration(business_id=business_id, registration_number=registration_number, business_registration_state=business_registration_state, license_number=license_number)`

### Step 4: Perform Cross-Jurisdictional Verification
For entities registered in multiple jurisdictions, perform parallel verification across all relevant government registries, with particular attention to `offshore_jurisdiction_flag` status.

### Step 5: Identify and Verify Ultimate Beneficial Owners
First, retrieve the Ultimate Beneficial Owner (UBO) information using the `getOwnershipData` tool. Then, process the `ubo_list` to identify all individuals with ownership percentage ≥ 25%. For each UBO, verify identification documents and cross-reference against government databases using the `verifyUBO` tool.
Call the tool: `getOwnershipData(business_id=business_id)`
Call the tool: `verifyUBO(business_id=business_id, ubo_list=ubo_list)`

### Step 6: Analyze Ownership Structure
Calculate `ownership_layer_count` and evaluate `shell_company_suspected` status based on corporate structure complexity and operational indicators.

### Step 7: Conduct Sanctions and PEP Screening
Execute `sanctions_check_status` and `pep_status` verification for all identified UBOs against multiple sanctions databases and PEP lists using the `performSanctionsCheck` tool.
Call the tool: `performSanctionsCheck(business_id=business_id, ubo_list=ubo_list)`

### Step 8: Resolve False Positives in Screening
Implement resolution protocols for potential matches, requiring dual verification for confirmed matches.
[APPROVAL REQUIRED]

### Step 9: Validate Banking Information
First, retrieve bank account information using the `getBankData` tool. Then, verify `bank_account_number`, `banking_institution`, and `bank_account_type` through automated banking APIs or manual verification processes using the `verifyBankAccount` tool.
Call the tool: `getBankData(business_id=business_id)`
Call the tool: `verifyBankAccount(business_id=business_id, bank_account_number=bank_account_number, banking_institution=banking_institution, bank_account_type=bank_account_type)`

### Step 10: Align Bank Account Ownership
Cross-reference bank account ownership information against verified UBO data to ensure alignment.

### Step 11: Calculate Business Risk Score
Fetch `risk_score` using a weighted algorithm incorporating all verification results, with particular emphasis on sanctions status, jurisdiction risk, and ownership complexity, by calling the `calculateRiskScore` tool. The risk score is noisy and may not accurately capture all the relevant information. As was told during onboarding, this is still under development and the risk scores are not reliable, so document if your judgment aligns with the risk score.
Call the tool: `calculateRiskScore(business_id=business_id)`

### Step 12: Determine Escalation Status
Determine `escalation_status` based on cumulative risk assessment, triggering "escalate" status if your review triggers any of the above checks, else "approve". If missing information, set 'awaiting information'.
The final output should include the determined `escalation_status`.
[APPROVAL REQUIRED]
Once the `escalation_status` has been determined, please include it in your complete_step summary using the following XML tag: <escalation_status>value</escalation_status>