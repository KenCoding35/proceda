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
Access the payer portal using provider credentials and validate the patient's primary insurance coverage, including effective dates, benefit levels, copayment requirements, and network participation.
Call `validateInsurance` with `patient_id`, `insurance_provider`, `policy_number`, `group_number`, `coverage_start_date`, and `insurance_type`.
[APPROVAL REQUIRED]

### Step 2: Validate Prescription Benefits
Query the Pharmacy Benefit Management (PBM) database to confirm current prescription coverage, formulary compliance, prior authorization requirements, and copayment structure.
Call `validatePrescriptionBenefits` with `patient_id`, `prescription_insurance_provider`, and `prescription_policy_number`.
[APPROVAL REQUIRED]

### Step 3: Calculate Lifestyle Risk
Assess the patient's lifestyle factors, including smoking status, alcohol consumption frequency, and exercise patterns, to compute an aggregate lifestyle risk score.
Call `calculateLifestyleRisk` with `patient_id`, `smoking_status`, `alcohol_consumption`, and `exercise_frequency`.

### Step 4: Calculate Overall Clinical Risk
Review the patient's surgical history and chronic conditions, then combine this with the calculated lifestyle risk to generate a comprehensive overall risk index.
Call `calculateOverallRisk` with `patient_id`, `previous_surgeries`, `chronic_conditions`, and the `life_style_risk_level` obtained from Step 3.

### Step 5: Verify Pharmacy Network Participation
Query the preferred pharmacy database to confirm its network participation and document any special handling requirements.
Call `verifyPharmacy` with `patient_id`, `preferred_pharmacy_name`, `preferred_pharmacy_address`, and `pharmacy_phone`.
[APPROVAL REQUIRED]

### Step 6: Register Patient
Complete the patient registration process by confirming all eligibility criteria, including primary insurance validation, prescription benefit validation, calculated risk levels, and preferred pharmacy network status.
Call `registerPatient` with `patient_id`, the `insurance_validation` status from Step 1, the `prescription_insurance_validation` status from Step 2, the `life_style_risk_level` from Step 3, the `overall_risk_level` from Step 4, and the `pharmacy_check` status from Step 5.
[APPROVAL REQUIRED]