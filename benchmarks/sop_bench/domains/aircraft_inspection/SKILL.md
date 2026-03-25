---
name: aircraft-inspection
description: Conducts pre-flight airworthiness verification through multi-layered inspection of mechanical components, electrical systems, and maintenance records.
required_tools:
  - VerifyAircraftClearance
  - VerifyMechanicalComponents
  - VerifyElectricalSystems
  - ReportComponentIncident
  - ReportComponentMismatch
  - CrossCheckSpecifications
  - ReportCrossCheck
output_fields:
  - aircraft_ready
  - mechanical_inspection_result
  - electrical_inspection_result
  - component_incident_response
  - component_mismatch_response
  - cross_check_response
  - cross_check_reporting_response
---

### Step 1: Validate Aircraft Identification
Call `VerifyAircraftClearance` with `aircraft_id`, `tail_number`, `maintenance_record_id`, and `expected_departure_time` to validate aircraft identification against the Airworthiness Validation Matrix (AVM) and check maintenance records. Record the `aircraft_ready` result.

### Step 2: Inspect Mechanical Components
Call `VerifyMechanicalComponents` with `aircraft_id`, `component_serial_number`, `inspection_location_id`, `component_weight`, `physical_condition_observation`, and `installation_time`. Record the `mechanical_inspection_result` (success, fail, or retest).

### Step 3: Authenticate Electrical Systems
Call `VerifyElectricalSystems` with `aircraft_id`, `battery_status`, `circuit_continuity_check`, and `avionics_diagnostics_response`. Record the `electrical_inspection_result` (success, fail, or retest).

### Step 4: Report Component Incidents
Call `ReportComponentIncident` with `aircraft_id`, `mechanical_inspection_result` (from Step 2), and `electrical_inspection_result` (from Step 3). Record the `component_incident_response`.

### Step 5: Report Component Mismatches
Call `ReportComponentMismatch` with `aircraft_id`, `component_serial_number`, `installed_component_serial_number`, and `inspection_location_id`. Record the `component_mismatch_response`.

### Step 6: Cross-Check Specifications
Call `CrossCheckSpecifications` with `aircraft_id`, `component_weight`, `expected_component_weight`, `installation_time`, and `actual_inspection_time`. Record the `cross_check_response`.

### Step 7: Report Cross-Check Results
Call `ReportCrossCheck` with `maintenance_record_id`, `aircraft_id`, `component_incident_response` (from Step 4), and `component_mismatch_response` (from Step 5). Record the `cross_check_reporting_response`.
