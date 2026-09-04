import pytest
from app.db.session import SessionLocal
from app.models.clinical_constraint import ClinicalConstraint
from app.models.patient import Patient
from app.repositories.clinical_constraint_repository import (
    get_active_clinical_constraints,
)
from app.repositories.alternative_repository import (
    get_active_alternatives_for_medicine,
)
from app.schemas.substitution import (
    CheckStatus,
    DecisionStatus,
    RiskLevel,
    SubstitutionRequest,
)
from app.services.substitution_engine import (
    evaluate_hepatic_check,
    evaluate_pregnancy_check,
    evaluate_renal_check,
    evaluate_substitution_lookup,
)


def test_1_renal_matching_conflict_fails():
    """Verify that a patient with matching renal status (e.g., SEVERE) fails the renal check."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="Metformin 500mg Tablet",
        constraint_type="RENAL",
        constraint_rule="Contraindicated if renal status is SEVERE",
        severity="CRITICAL",
        evidence_source="Synthetic prototype guidelines",
    )
    res = evaluate_renal_check(
        patient_exists=True,
        renal_status="SEVERE",
        candidate_medicine="Metformin 500mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.CRITICAL
    assert "conflicts with patient's recorded renal status 'SEVERE'" in res.reason


def test_2_renal_no_conflict_passes():
    """Verify that a patient with NORMAL renal status passes the renal check."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="Metformin 500mg Tablet",
        constraint_type="RENAL",
        constraint_rule="Contraindicated if renal status is SEVERE",
        severity="CRITICAL",
    )
    res = evaluate_renal_check(
        patient_exists=True,
        renal_status="NORMAL",
        candidate_medicine="Metformin 500mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.PASS


def test_3_renal_conflict_causes_blocked_decision():
    """Verify that a renal conflict produces BLOCKED decision with recommended_medicine=None."""
    patient = Patient(id=1, patient_code="PAT-TEST", age=65, sex="Male", renal_status="SEVERE")
    alts = get_active_alternatives_for_medicine(SessionLocal(), "Metformin 500mg Tablet")
    constraints = [
        ClinicalConstraint(
            id=1,
            medicine_name="Gliclazide 80mg Tablet",
            constraint_type="RENAL",
            constraint_rule="Contraindicated if renal status is SEVERE",
            severity="CRITICAL",
        )
    ]
    req = SubstitutionRequest(patient_id=1, prescription_id=1, prescription_medication_id=1, original_medicine="Metformin 500mg Tablet")
    
    # Evaluate with Gliclazide candidate
    cand = type("Alt", (), {"source_medicine": "Metformin 500mg Tablet", "alternative_medicine": "Gliclazide 80mg Tablet", "alternative_ingredient": "Gliclazide"})()
    decision = evaluate_substitution_lookup(req, [cand], patient=patient, clinical_constraints=constraints)

    assert decision.decision_status == DecisionStatus.BLOCKED
    assert decision.recommended_medicine is None
    assert decision.requires_human_confirmation is True


def test_4_renal_severity_mapping():
    """Verify that ClinicalConstraint.severity maps correctly to RiskLevel."""
    c_critical = ClinicalConstraint(id=1, medicine_name="Med A", constraint_type="RENAL", constraint_rule="Rule SEVERE", severity="CRITICAL")
    res_crit = evaluate_renal_check(True, "SEVERE", "Med A", [c_critical])
    assert res_crit.severity == RiskLevel.CRITICAL

    c_high = ClinicalConstraint(id=2, medicine_name="Med B", constraint_type="RENAL", constraint_rule="Rule MODERATE", severity="MODERATE")
    res_high = evaluate_renal_check(True, "MODERATE", "Med B", [c_high])
    assert res_high.severity == RiskLevel.HIGH


def test_5_non_matching_renal_status_does_not_block():
    """Verify that a patient with MILD renal status passes when constraint requires SEVERE."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="Ciprofloxacin 500mg Tablet",
        constraint_type="RENAL",
        constraint_rule="Requires dose reduction if renal status is SEVERE",
        severity="HIGH",
    )
    res = evaluate_renal_check(True, "MILD", "Ciprofloxacin 500mg Tablet", [c])
    assert res.status == CheckStatus.PASS


def test_6_hepatic_matching_conflict_fails_and_blocks():
    """Verify that a hepatic conflict (e.g. SEVERE hepatic status) fails hepatic check and blocks decision."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="Atorvastatin 20mg Tablet",
        constraint_type="HEPATIC",
        constraint_rule="Contraindicated if hepatic status is SEVERE",
        severity="CRITICAL",
    )
    res = evaluate_hepatic_check(True, "SEVERE", "Atorvastatin 20mg Tablet", [c])
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.CRITICAL

    patient = Patient(id=2, patient_code="PAT-HEPATIC", age=50, sex="Female", hepatic_status="SEVERE")
    req = SubstitutionRequest(patient_id=2, prescription_id=1, prescription_medication_id=1, original_medicine="Atorvastatin 20mg Tablet")
    cand = type("Alt", (), {"source_medicine": "Atorvastatin 20mg Tablet", "alternative_medicine": "Rosuvastatin 10mg Tablet", "alternative_ingredient": "Rosuvastatin"})()
    decision = evaluate_substitution_lookup(req, [cand], patient=patient, clinical_constraints=[c])

    assert decision.decision_status == DecisionStatus.BLOCKED
    assert decision.recommended_medicine is None


def test_7_hepatic_no_conflict_passes():
    """Verify that NORMAL hepatic status passes hepatic check."""
    c = ClinicalConstraint(id=1, medicine_name="Med A", constraint_type="HEPATIC", constraint_rule="Rule SEVERE", severity="HIGH")
    res = evaluate_hepatic_check(True, "NORMAL", "Med A", [c])
    assert res.status == CheckStatus.PASS


def test_8_pregnancy_matching_conflict_fails_and_blocks():
    """Verify that a PREGNANT patient attempting a contraindicated drug fails pregnancy check and blocks."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="Losartan 50mg Tablet",
        constraint_type="PREGNANCY",
        constraint_rule="Contraindicated during PREGNANCY (Teratogenic risk)",
        severity="CRITICAL",
        evidence_source="Synthetic prototype guidelines",
    )
    res = evaluate_pregnancy_check(True, "PREGNANT", "Losartan 50mg Tablet", [c])
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.CRITICAL
    assert "contraindicated during pregnancy" in res.reason.lower()

    patient = Patient(id=3, patient_code="PAT-PREG", age=28, sex="Female", pregnancy_status="PREGNANT")
    req = SubstitutionRequest(patient_id=3, prescription_id=1, prescription_medication_id=1, original_medicine="Lisinopril 10mg Tablet")
    cand = type("Alt", (), {"source_medicine": "Lisinopril 10mg Tablet", "alternative_medicine": "Losartan 50mg Tablet", "alternative_ingredient": "Losartan"})()
    decision = evaluate_substitution_lookup(req, [cand], patient=patient, clinical_constraints=[c])

    assert decision.decision_status == DecisionStatus.BLOCKED
    assert decision.recommended_medicine is None


def test_9_pregnancy_no_conflict_passes():
    """Verify that NOT_PREGNANT or NOT_APPLICABLE status passes pregnancy check."""
    c = ClinicalConstraint(id=1, medicine_name="Losartan 50mg Tablet", constraint_type="PREGNANCY", constraint_rule="Rule PREGNANCY", severity="CRITICAL")
    res1 = evaluate_pregnancy_check(True, "NOT_PREGNANT", "Losartan 50mg Tablet", [c])
    res2 = evaluate_pregnancy_check(True, "NOT_APPLICABLE", "Losartan 50mg Tablet", [c])
    assert res1.status == CheckStatus.PASS
    assert res2.status == CheckStatus.PASS


def test_10_case_and_whitespace_normalization():
    """Verify case-insensitive and whitespace-normalized clinical constraint matching."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="  Losartan 50mg Tablet  ",
        constraint_type="  PREGNANCY  ",
        constraint_rule="Contraindicated during PREGNANCY",
        severity="CRITICAL",
    )
    res = evaluate_pregnancy_check(True, "  pregnant  ", "losartan 50mg tablet", [c])
    assert res.status == CheckStatus.FAIL


def test_11_evidence_and_explainable_reasons_included():
    """Verify that clinical CheckResults contain human-readable reasons and evidence sources."""
    c = ClinicalConstraint(
        id=5,
        medicine_name="Ciprofloxacin 500mg Tablet",
        constraint_type="RENAL",
        constraint_rule="Requires dose reduction if renal status is SEVERE",
        severity="HIGH",
        evidence_source="Synthetic Prototype Rule Source ID 102",
    )
    res = evaluate_renal_check(True, "SEVERE", "Ciprofloxacin 500mg Tablet", [c])
    assert res.evidence is not None
    assert "Synthetic Prototype Rule Source ID 102" in res.evidence
    assert "conflicts with patient's recorded renal status 'SEVERE'" in res.reason


def test_12_pipeline_order_and_history_retention():
    """Verify all evaluated checks are retained in DecisionResult.checks in pipeline order."""
    patient = Patient(id=1, patient_code="PAT-0001", age=45, sex="Female", renal_status="NORMAL", hepatic_status="NORMAL", pregnancy_status="NOT_PREGNANT")
    alts = get_active_alternatives_for_medicine(SessionLocal(), "Amoxicillin 500mg Capsule")
    
    req = SubstitutionRequest(patient_id=1, prescription_id=1, prescription_medication_id=1, original_medicine="Amoxicillin 500mg Capsule")
    decision = evaluate_substitution_lookup(req, alts, patient=patient, allergies=[], clinical_constraints=[])

    check_names = [c.check_name for c in decision.checks]
    assert check_names == ["approved_alternative", "allergy", "renal", "hepatic", "pregnancy", "age", "drug_interaction", "dosage", "stock"]


def test_13_deterministic_clinical_evaluations():
    """Verify that identical inputs produce identical clinical decision outputs."""
    c = ClinicalConstraint(id=1, medicine_name="Med A", constraint_type="RENAL", constraint_rule="Rule SEVERE", severity="HIGH")
    res1 = evaluate_renal_check(True, "SEVERE", "Med A", [c])
    res2 = evaluate_renal_check(True, "SEVERE", "Med A", [c])
    assert res1.model_dump_json() == res2.model_dump_json()
