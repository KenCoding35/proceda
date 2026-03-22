---
name: patient-intake
description: Establishes a comprehensive framework for the intake and registration of new patients, encompassing demographic data collection, insurance verification, risk stratification, and pharmacy network validation.
required_tools:
  - validateInsurance
  - validatePrescriptionBenefits
  - calculateLifestyleRisk
  - calculateOverallRisk
  - verifyPharmacy
  - registerPatient
---

### Step 1: Verify Primary Insurance
Access the payer portal using provider credentials to verify the patient's primary insurance coverage status, effective dates, benefit levels, copayment requirements, and network participation. Document authorization requirements.
Use the `validateInsurance` tool to perform this check.
Input for `validateInsurance`:
- `insurance_card_details`: Details from the patient's current insurance card(s).
[OPTIONAL] Collect government-issued photo identification.

### Step 2: Validate Prescription Benefits
Query the PBM database to verify current prescription coverage, formulary compliance parameters, prior authorization requirements, specialty pharmacy protocols, and copayment structure.
Use the `validatePrescriptionBenefits` tool to perform this validation.
Input for `validatePrescriptionBenefits`:
- `pharmacy_benefit_card_details`: Details from the patient's pharmacy benefit card.
[OPTIONAL] Document prior authorization documentation if provided.

### Step 3: Evaluate Lifestyle Risk
Calculate the patient's lifestyle risk index based on their medical history questionnaire, including smoking status, alcohol consumption frequency, and exercise patterns.
Use the `calculateLifestyleRisk` tool to compute the aggregate lifestyle score.
Input for `calculateLifestyleRisk`:
- `smoking_status`: Patient's smoking risk index (e.g., Never, Former, Current).
- `alcohol_consumption_frequency`: Patient's alcohol consumption frequency (e.g., None, Occasional, Moderate, Heavy).
- `exercise_patterns`: Patient's exercise patterns (e.g., 5+ times, 3-4 times, 1-2 times, None).

### Step 4: Assess Overall Clinical Risk
Review the patient's surgical history chronology and evaluate chronic condition severity to calculate a comorbidity interaction score and generate a weighted risk factor index. This incorporates the previously calculated lifestyle risk.
Use the `calculateOverallRisk` tool to generate the comprehensive patient risk level.
Input for `calculateOverallRisk`:
- `surgical_history`: Chronological record of the patient's surgical history.
- `chronic_conditions`: Evaluation of the patient's chronic condition severity.
- `life_style_risk_level`: The aggregate lifestyle score obtained from Step 3.

### Step 5: Verify Pharmacy Network
Query the preferred pharmacy database to verify pharmacy network participation and document any special handling requirements.
Use the `verifyPharmacy` tool to confirm the pharmacy check status.
Input for `verifyPharmacy`:
- `preferred_pharmacy_details`: Details of the patient's preferred pharmacy.

### Step 6: Complete Patient Registration
Finalize the patient registration process by confirming the successful validation of insurance status, prescription benefits, risk levels, and pharmacy network participation. Registration will only proceed if all required validations pass successfully.
Use the `registerPatient` tool to complete the registration.
Input for `registerPatient`:
- `insurance_validation_status`: The status result from Step 1.
- `prescription_insurance_validation_status`: The status result from Step 2.
- `life_style_risk_level`: The lifestyle risk level obtained from Step 3.
- `overall_risk_level`: The overall risk level obtained from Step 4.
- `pharmacy_check_status`: The status result from Step 5.
[OPTIONAL] Process release of medical records forms if provided.