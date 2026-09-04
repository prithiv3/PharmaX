# Database Schema Guide — PostgreSQL (`pharmacy_substitution_db`)

This document details the PostgreSQL database tables, primary keys, foreign keys, relationships, and column schemas implemented in the system.

---

## Entity Relationship Overview

```
patients (1) ────< allergies (N)
   │ (1)
   └───< prescriptions (N) ────< prescription_medications (N)
                                         │ (1)
                                         └───< substitution_decisions (N) ────< pharmacist_reviews (N)
                                                       │ (1)
                                                       └───< audit_logs (N)

medicine_alternatives (1) ────< clinical_constraints (N)
          │ (1)
          └───────────< medicine_stocks (N)
```

---

## Table Schemas

### 1. `patients`
Stores demographic context and baseline organ function profile.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique patient record identifier |
| `patient_code` | `VARCHAR(50)` | `UNIQUE, NOT NULL, INDEX` | Unique patient code (e.g. `PAT-0001`) |
| `first_name` | `VARCHAR(100)` | `NOT NULL` | Patient first name |
| `last_name` | `VARCHAR(100)` | `NOT NULL` | Patient last name |
| `age` | `INTEGER` | `NOT NULL` | Patient age in years |
| `gender` | `VARCHAR(20)` | `NOT NULL` | Gender (`MALE`, `FEMALE`, `OTHER`) |
| `is_pregnant` | `BOOLEAN` | `NOT NULL, DEFAULT FALSE` | Pregnancy status |
| `egfr` | `FLOAT` | `NULLABLE` | Estimated Glomerular Filtration Rate (mL/min/1.73m²) |
| `has_hepatic_impairment`| `BOOLEAN` | `NOT NULL, DEFAULT FALSE` | Hepatic impairment status |
| `created_at` | `TIMESTAMP` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp |

---

### 2. `allergies`
Stores patient ingredient hypersensitivity records.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique allergy record identifier |
| `patient_id` | `INTEGER` | `FOREIGN KEY(patients.id), NOT NULL` | Associated patient ID |
| `allergen_name` | `VARCHAR(150)`| `NOT NULL, INDEX` | Allergen compound name (e.g. `PENICILLIN`) |
| `reaction_severity`| `VARCHAR(50)` | `NOT NULL` | Severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) |
| `reaction_description`| `TEXT` | `NULLABLE` | Clinical description of reaction |
| `created_at` | `TIMESTAMP` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp |

---

### 3. `prescriptions`
Stores prescription header context.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique prescription header identifier |
| `patient_id` | `INTEGER` | `FOREIGN KEY(patients.id), NOT NULL` | Associated patient ID |
| `prescription_code`| `VARCHAR(50)`| `UNIQUE, NOT NULL` | Unique prescription code (e.g. `RX-0001`) |
| `prescriber_name` | `VARCHAR(150)`| `NOT NULL` | Prescribing physician name |
| `created_at` | `TIMESTAMP` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Prescription issue timestamp |

---

### 4. `prescription_medications`
Stores prescribed line-item medication details.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique line-item identifier |
| `prescription_id` | `INTEGER` | `FOREIGN KEY(prescriptions.id), NOT NULL` | Associated prescription header ID |
| `medicine_name` | `VARCHAR(200)`| `NOT NULL` | Prescribed medicine name |
| `active_ingredient`| `VARCHAR(150)`| `NOT NULL` | Active pharmaceutical ingredient |
| `dosage_mg` | `FLOAT` | `NOT NULL` | Unit dose in milligrams |
| `frequency_per_day`| `INTEGER` | `NOT NULL` | Administration frequency per day |
| `created_at` | `TIMESTAMP` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp |

---

### 5. `medicine_alternatives`
Stores candidate alternative drug mappings and dosage bounds.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique alternative record identifier |
| `original_medicine`| `VARCHAR(200)`| `NOT NULL, INDEX` | Prescribed drug name mapping |
| `alternative_medicine`| `VARCHAR(200)`| `NOT NULL` | Candidate alternative drug name |
| `active_ingredient`| `VARCHAR(150)`| `NOT NULL` | Active ingredient compound |
| `dosage_mg` | `FLOAT` | `NOT NULL` | Unit dosage in milligrams |
| `max_daily_dose_mg`| `FLOAT` | `NOT NULL` | Maximum safe daily dosage boundary |
| `risk_level` | `VARCHAR(20)` | `NOT NULL` | Risk level classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) |
| `is_approved` | `BOOLEAN` | `NOT NULL, DEFAULT TRUE` | Regulatory approval mapping status |
| `created_at` | `TIMESTAMP` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp |

---

### 6. `clinical_constraints`
Stores clinical contraindication boundaries for alternatives.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique constraint identifier |
| `alternative_id` | `INTEGER` | `FOREIGN KEY(medicine_alternatives.id), NOT NULL` | Associated alternative ID |
| `min_age` | `INTEGER` | `NULLABLE` | Minimum safe patient age in years |
| `max_age` | `INTEGER` | `NULLABLE` | Maximum safe patient age in years |
| `min_egfr` | `FLOAT` | `NULLABLE` | Minimum safe eGFR (mL/min/1.73m²) |
| `contraindicated_in_pregnancy`| `BOOLEAN`| `NOT NULL, DEFAULT FALSE` | Pregnancy contraindication flag |
| `contraindicated_in_hepatic_impairment`| `BOOLEAN`| `NOT NULL, DEFAULT FALSE` | Hepatic impairment contraindication flag |
| `interacting_drugs` | `TEXT` | `NULLABLE` | Comma-separated list of interacting drugs |
| `created_at` | `TIMESTAMP` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp |

---

### 7. `medicine_stocks`
Stores physical inventory stock levels in pharmacy storage.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique inventory stock identifier |
| `alternative_id` | `INTEGER` | `FOREIGN KEY(medicine_alternatives.id), NOT NULL` | Associated alternative ID |
| `usable_stock` | `INTEGER` | `NOT NULL, DEFAULT 0` | Available unexpired physical inventory count |
| `batch_number` | `VARCHAR(50)` | `NOT NULL` | Inventory batch identifier |
| `expiration_date` | `DATE` | `NOT NULL` | Stock expiration date |
| `created_at` | `TIMESTAMP` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp |

---

### 8. `substitution_decisions`
Stores persisted decision support evaluation results.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique decision record identifier |
| `patient_id` | `INTEGER` | `FOREIGN KEY(patients.id), NOT NULL` | Associated patient ID |
| `prescription_id` | `INTEGER` | `FOREIGN KEY(prescriptions.id), NOT NULL` | Associated prescription ID |
| `prescription_medication_id`| `INTEGER` | `FOREIGN KEY(prescription_medications.id), NOT NULL` | Prescribed medication ID |
| `original_medicine`| `VARCHAR(200)`| `NOT NULL` | Prescribed drug name |
| `recommended_medicine`| `VARCHAR(200)`| `NULLABLE` | System recommended alternative drug name |
| `decision_status` | `VARCHAR(30)` | `NOT NULL, INDEX` | Status (`RECOMMENDED`, `BLOCKED`, `NEEDS_REVIEW`, `APPROVED`, `REJECTED`, `OVERRIDDEN`) |
| `risk_level` | `VARCHAR(20)` | `NOT NULL` | Overall decision risk level |
| `confidence_score`| `FLOAT` | `NOT NULL` | Evaluated confidence score (0.0 to 1.0) |
| `requires_human_confirmation`| `BOOLEAN`| `NOT NULL, DEFAULT TRUE` | Human confirmation requirement flag |
| `reason` | `TEXT` | `NOT NULL` | Primary clinical decision justification |
| `checks_json` | `TEXT` | `NOT NULL` | JSON string of all 9 safety check results |
| `created_at` | `TIMESTAMP` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Evaluation timestamp |

---

### 9. `pharmacist_reviews`
Stores human-in-the-loop pharmacist review and override submissions.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique review identifier |
| `decision_id` | `INTEGER` | `FOREIGN KEY(substitution_decisions.id), NOT NULL` | Associated decision ID |
| `pharmacist_code`| `VARCHAR(50)` | `NOT NULL` | Reviewing pharmacist identifier code |
| `review_status` | `VARCHAR(30)` | `NOT NULL` | Submitted review action (`APPROVED`, `REJECTED`, `OVERRIDDEN`) |
| `override_reason` | `TEXT` | `NULLABLE` | Mandatory text justification for clinical overrides |
| `review_notes` | `TEXT` | `NULLABLE` | Internal pharmacy notes |
| `created_at` | `TIMESTAMP` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Review submission timestamp |

---

### 10. `audit_logs`
Stores immutable compliance audit trail log entries.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique audit log identifier |
| `decision_id` | `INTEGER` | `FOREIGN KEY(substitution_decisions.id), NOT NULL` | Associated decision ID |
| `action` | `VARCHAR(50)` | `NOT NULL` | Audit action (`DECISION_EVALUATED`, `PHARMACIST_REVIEW`) |
| `actor_code` | `VARCHAR(50)` | `NULLABLE` | Actor code (`SYSTEM` or pharmacist code) |
| `previous_status` | `VARCHAR(30)` | `NULLABLE` | Previous decision status |
| `new_status` | `VARCHAR(30)` | `NOT NULL` | Updated decision status |
| `reason` | `TEXT` | `NOT NULL` | Audit event explanation |
| `created_at` | `TIMESTAMP` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Event timestamp |
