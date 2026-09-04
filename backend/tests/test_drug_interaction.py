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
    evaluate_drug_interaction_check,
    evaluate_substitution_lookup,
)


def test_1_no_interaction_passes():
    """Verify that when no prescribed medication conflicts with interaction rules, the check passes."""
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Amoxicillin 500mg Capsule",
        active_ingredient="Amoxicillin",
        strength="500mg",
        dosage_form="Capsule",
    )
    c = ClinicalConstraint(
        id=1,
        medicine_name="Clarithromycin 250mg Tablet",
        constraint_type="DRUG_INTERACTION",
        constraint_rule="Severe interaction with Atorvastatin (Rhabdomyolysis risk)",
        severity="CRITICAL",
    )
    res = evaluate_drug_interaction_check(
        patient_exists=True,
        prescribed_medications=[med],
        candidate_medicine="Clarithromycin 250mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.PASS
    assert "No active drug interaction conflict was found" in res.reason


def test_2_matching_interaction_fails_and_blocks():
    """Verify that a matching drug interaction (Clarithromycin vs prescribed Atorvastatin) fails and blocks."""
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Atorvastatin 20mg Tablet",
        active_ingredient="Atorvastatin",
        strength="20mg",
        dosage_form="Tablet",
    )
    c = ClinicalConstraint(
        id=1,
        medicine_name="Clarithromycin 250mg Tablet",
        constraint_type="DRUG_INTERACTION",
        constraint_rule="Severe interaction with Atorvastatin (Rhabdomyolysis risk)",
        severity="CRITICAL",
        evidence_source="Synthetic drug interaction guidelines",
    )
    res = evaluate_drug_interaction_check(
        patient_exists=True,
        prescribed_medications=[med],
        candidate_medicine="Clarithromycin 250mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.CRITICAL
    assert "has a drug interaction with patient's medication 'Atorvastatin 20mg Tablet'" in res.reason
    assert res.evidence is not None
    assert "Severe interaction with Atorvastatin" in res.evidence


def test_3_multiple_prescribed_medications_evaluated():
    """Verify all prescribed medications are evaluated and any matching interaction triggers FAIL."""
    m1 = PrescriptionMedication(id=1, prescription_id=1, medicine_name="Metformin 500mg Tablet", active_ingredient="Metformin", strength="500mg", dosage_form="Tablet")
    m2 = PrescriptionMedication(id=2, prescription_id=1, medicine_name="Atorvastatin 20mg Tablet", active_ingredient="Atorvastatin", strength="20mg", dosage_form="Tablet")
    c = ClinicalConstraint(
        id=1,
        medicine_name="Clarithromycin 250mg Tablet",
        constraint_type="DRUG_INTERACTION",
        constraint_rule="Severe interaction with Atorvastatin",
        severity="CRITICAL",
    )
    res = evaluate_drug_interaction_check(
        patient_exists=True,
        prescribed_medications=[m1, m2],
        candidate_medicine="Clarithromycin 250mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.FAIL
    assert "Atorvastatin 20mg Tablet" in res.reason


def test_4_inactive_interaction_constraint_excluded():
    """Verify that inactive interaction constraints (is_active=False) do NOT trigger a failure."""
    c_inactive = ClinicalConstraint(
        id=1,
        medicine_name="Clarithromycin 250mg Tablet",
        constraint_type="DRUG_INTERACTION",
        constraint_rule="Severe interaction with Atorvastatin",
        severity="CRITICAL",
        is_active=False,
    )
    # Passed constraint list contains only active constraints
    res = evaluate_drug_interaction_check(
        patient_exists=True,
        prescribed_medications=[],
        candidate_medicine="Clarithromycin 250mg Tablet",
        constraints=[],
    )
    assert res.status == CheckStatus.PASS


def test_5_case_and_whitespace_normalization():
    """Verify case-insensitive and whitespace-normalized interaction matching."""
    med = PrescriptionMedication(id=1, prescription_id=1, medicine_name="  Atorvastatin 20mg Tablet  ", active_ingredient="  ATORVASTATIN  ", strength="20mg", dosage_form="Tablet")
    c = ClinicalConstraint(
        id=1,
        medicine_name="  Clarithromycin 250mg Tablet  ",
        constraint_type="  DRUG_INTERACTION  ",
        constraint_rule="Severe interaction with atorvastatin",
        severity="CRITICAL",
    )
    res = evaluate_drug_interaction_check(
        patient_exists=True,
        prescribed_medications=[med],
        candidate_medicine="clarithromycin 250mg tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.FAIL


def test_6_substring_matching_does_not_trigger_false_positive():
    """Verify that unrelated substring medicine names do NOT trigger interaction false positives."""
    med = PrescriptionMedication(id=1, prescription_id=1, medicine_name="Ato", active_ingredient="Ato", strength="10mg", dosage_form="Tablet")
    c = ClinicalConstraint(
        id=1,
        medicine_name="Clarithromycin 250mg Tablet",
        constraint_type="DRUG_INTERACTION",
        constraint_rule="Severe interaction with Atorvastatin",
        severity="CRITICAL",
    )
    res = evaluate_drug_interaction_check(
        patient_exists=True,
        prescribed_medications=[med],
        candidate_medicine="Clarithromycin 250mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.PASS


def test_7_missing_patient_and_prescription_safety():
    """Verify missing patient or missing prescription medication data returns CheckStatus.FAIL."""
    res1 = evaluate_drug_interaction_check(
        patient_exists=False,
        prescribed_medications=[],
        candidate_medicine="Clarithromycin 250mg Tablet",
        constraints=[],
    )
    res2 = evaluate_drug_interaction_check(
        patient_exists=True,
        prescribed_medications=None,
        candidate_medicine="Clarithromycin 250mg Tablet",
        constraints=[],
    )
    assert res1.status == CheckStatus.FAIL
    assert res2.status == CheckStatus.FAIL
    assert res1.severity == RiskLevel.HIGH
    assert res2.severity == RiskLevel.HIGH


def test_8_pipeline_order_includes_all_7_checks():
    """Verify all 7 checks are evaluated in execution order."""
    patient = Patient(id=1, patient_code="PAT-0001", age=45, sex="Female")
    cand = type(
        "Alt",
        (),
        {
            "source_medicine": "Azithromycin 250mg Tablet",
            "alternative_medicine": "Clarithromycin 250mg Tablet",
            "alternative_ingredient": "Clarithromycin",
        },
    )()
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Azithromycin 250mg Tablet",
    )

    decision = evaluate_substitution_lookup(
        req, [cand], patient=patient, allergies=[], clinical_constraints=[], prescribed_medications=[]
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


def test_9_deterministic_interaction_evaluations():
    """Verify that identical inputs produce identical drug interaction decision outputs."""
    med = PrescriptionMedication(id=1, prescription_id=1, medicine_name="Atorvastatin 20mg Tablet", active_ingredient="Atorvastatin", strength="20mg", dosage_form="Tablet")
    c = ClinicalConstraint(id=1, medicine_name="Clarithromycin 250mg Tablet", constraint_type="DRUG_INTERACTION", constraint_rule="Severe interaction with Atorvastatin", severity="CRITICAL")

    res1 = evaluate_drug_interaction_check(True, [med], "Clarithromycin 250mg Tablet", [c])
    res2 = evaluate_drug_interaction_check(True, [med], "Clarithromycin 250mg Tablet", [c])
    assert res1.model_dump_json() == res2.model_dump_json()
