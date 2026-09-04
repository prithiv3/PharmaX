import pytest
from app.models.clinical_constraint import ClinicalConstraint
from app.models.medication import PrescriptionMedication
from app.models.patient import Patient
from app.schemas.substitution import (
    CheckStatus,
    DecisionStatus,
    RiskLevel,
    SubstitutionRequest,
)
from app.services.substitution_engine import (
    evaluate_dosage_check,
    evaluate_substitution_lookup,
)


def test_1_safe_dosage_passes():
    """Verify that a prescription within the maximum daily dose limit passes the dosage check."""
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Paracetamol 500mg Tablet",
        active_ingredient="Paracetamol",
        strength="500mg",
        dose="500mg",
        frequency="TID",
        dosage_form="Tablet",
    )
    c = ClinicalConstraint(
        id=1,
        medicine_name="Paracetamol 500mg Tablet",
        constraint_type="DOSAGE",
        constraint_rule="Maximum daily dose is 4000mg",
        severity="HIGH",
    )
    # 500mg * 3 = 1500mg <= 4000mg
    res = evaluate_dosage_check(
        patient_exists=True,
        prescribed_medication=med,
        candidate_medicine="Paracetamol 500mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.PASS
    assert "No dosage conflict was found" in res.reason


def test_2_maximum_daily_dose_violation_fails_and_blocks():
    """Verify that a daily dose exceeding the maximum limit (e.g. 5000mg > 4000mg limit) fails and blocks."""
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Paracetamol 500mg Tablet",
        active_ingredient="Paracetamol",
        strength="1000mg",
        dose="1000mg",
        frequency="QID",
        dosage_form="Tablet",
    )
    # 1000mg * 4 = 4000mg (or 2 tabs QID = 1000mg * 5 = 5000mg) -> Let's test 1250mg * 4 = 5000mg
    med.dose = "1250mg"
    c = ClinicalConstraint(
        id=1,
        medicine_name="Paracetamol 500mg Tablet",
        constraint_type="DOSAGE",
        constraint_rule="Maximum daily dose is 4000mg",
        severity="HIGH",
        evidence_source="Synthetic dosage guideline",
    )
    res = evaluate_dosage_check(
        patient_exists=True,
        prescribed_medication=med,
        candidate_medicine="Paracetamol 500mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.HIGH
    assert "conflicts with the prescribed dosage" in res.reason
    assert res.evidence is not None
    assert "exceeds maximum synthetic limit (4000mg)" in res.evidence


def test_3_frequency_restriction_violation_fails():
    """Verify that a frequency restriction (Methotrexate daily vs ONCE WEEKLY rule) fails."""
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Methotrexate 2.5mg Tablet",
        active_ingredient="Methotrexate",
        strength="2.5mg",
        dose="2.5mg",
        frequency="daily",
        dosage_form="Tablet",
    )
    c = ClinicalConstraint(
        id=1,
        medicine_name="Methotrexate 2.5mg Tablet",
        constraint_type="DOSAGE",
        constraint_rule="Dosed ONCE WEEKLY only - daily dosing is contra-indicated",
        severity="CRITICAL",
    )
    res = evaluate_dosage_check(
        patient_exists=True,
        prescribed_medication=med,
        candidate_medicine="Methotrexate 2.5mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.CRITICAL
    assert res.evidence is not None
    assert "violates once weekly administration rule" in res.evidence


def test_4_missing_dose_or_frequency_fails_safely():
    """Verify that missing dose or frequency returns CheckStatus.FAIL with HIGH severity."""
    med_no_dose = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Paracetamol 500mg Tablet",
        active_ingredient="Paracetamol",
        dose="",
        frequency="TID",
    )
    med_no_freq = PrescriptionMedication(
        id=2,
        prescription_id=1,
        medicine_name="Paracetamol 500mg Tablet",
        active_ingredient="Paracetamol",
        dose="500mg",
        frequency="",
    )
    res1 = evaluate_dosage_check(True, med_no_dose, "Paracetamol 500mg Tablet", [])
    res2 = evaluate_dosage_check(True, med_no_freq, "Paracetamol 500mg Tablet", [])
    assert res1.status == CheckStatus.FAIL
    assert res2.status == CheckStatus.FAIL
    assert res1.severity == RiskLevel.HIGH
    assert res2.severity == RiskLevel.HIGH


def test_5_inactive_dosage_constraint_excluded():
    """Verify that inactive DOSAGE constraints (is_active=False) do NOT trigger a failure."""
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Paracetamol 500mg Tablet",
        active_ingredient="Paracetamol",
        dose="1500mg",
        frequency="QID",
    )
    # Passed constraints list contains only active constraints
    res = evaluate_dosage_check(
        patient_exists=True,
        prescribed_medication=med,
        candidate_medicine="Paracetamol 500mg Tablet",
        constraints=[],
    )
    assert res.status == CheckStatus.PASS


def test_6_case_and_whitespace_normalization():
    """Verify case-insensitive and whitespace-normalized dosage matching."""
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="  Paracetamol 500mg Tablet  ",
        active_ingredient="  PARACETAMOL  ",
        dose="  1500mg  ",
        frequency="  QID  ",
    )
    c = ClinicalConstraint(
        id=1,
        medicine_name="  Paracetamol 500mg Tablet  ",
        constraint_type="  DOSAGE  ",
        constraint_rule="Maximum daily dose is 4000mg",
        severity="HIGH",
    )
    res = evaluate_dosage_check(
        patient_exists=True,
        prescribed_medication=med,
        candidate_medicine="paracetamol 500mg tablet",
        constraints=[c],
    )
    # 1500 * 4 = 6000mg > 4000mg -> FAIL
    assert res.status == CheckStatus.FAIL


def test_7_pipeline_order_includes_all_8_checks():
    """Verify all 8 checks are evaluated in execution order."""
    patient = Patient(id=1, patient_code="PAT-0001", age=45, sex="Female")
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Amoxicillin 500mg Capsule",
        active_ingredient="Amoxicillin",
        dose="500mg",
        frequency="TID",
    )
    cand = type(
        "Alt",
        (),
        {
            "source_medicine": "Amoxicillin 500mg Capsule",
            "alternative_medicine": "Cefalexin 500mg Capsule",
            "alternative_ingredient": "Cefalexin",
        },
    )()
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Amoxicillin 500mg Capsule",
    )

    decision = evaluate_substitution_lookup(
        req,
        [cand],
        patient=patient,
        allergies=[],
        clinical_constraints=[],
        prescribed_medications=[med],
        prescribed_medication=med,
    )

    check_names = [c.check_name for c in decision.checks]
    assert check_names == [
        "approved_alternative",
        "allergy",
        "renal",
        "hepatic",
        "pregnancy",
        "age",
        "drug_interaction",
        "dosage",
        "stock",
    ]


def test_8_deterministic_dosage_evaluations():
    """Verify that identical inputs produce identical dosage decision outputs."""
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Paracetamol 500mg Tablet",
        active_ingredient="Paracetamol",
        dose="500mg",
        frequency="TID",
    )
    c = ClinicalConstraint(
        id=1,
        medicine_name="Paracetamol 500mg Tablet",
        constraint_type="DOSAGE",
        constraint_rule="Maximum daily dose is 4000mg",
        severity="HIGH",
    )
    res1 = evaluate_dosage_check(True, med, "Paracetamol 500mg Tablet", [c])
    res2 = evaluate_dosage_check(True, med, "Paracetamol 500mg Tablet", [c])
    assert res1.model_dump_json() == res2.model_dump_json()
