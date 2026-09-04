import pytest
from app.models.clinical_constraint import ClinicalConstraint
from app.models.patient import Patient
from app.schemas.substitution import (
    CheckStatus,
    DecisionStatus,
    RiskLevel,
    SubstitutionRequest,
)
from app.services.substitution_engine import (
    evaluate_age_check,
    evaluate_substitution_lookup,
)


def test_1_patient_satisfying_age_constraint_passes():
    """Verify that an adult patient (e.g., 25 years old) passes pediatric age constraints."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="Ciprofloxacin 500mg Tablet",
        constraint_type="AGE",
        constraint_rule="Contraindicated in pediatric patients under 18 years old",
        severity="HIGH",
    )
    res = evaluate_age_check(
        patient_exists=True,
        patient_age=25,
        candidate_medicine="Ciprofloxacin 500mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.PASS
    assert "No recorded age conflict was found" in res.reason


def test_2_patient_violating_age_constraint_fails():
    """Verify that a pediatric patient (e.g., 12 years old) fails pediatric age constraints under 18."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="Ciprofloxacin 500mg Tablet",
        constraint_type="AGE",
        constraint_rule="Contraindicated in pediatric patients under 18 years old",
        severity="HIGH",
        evidence_source="Synthetic pediatric safety rules",
    )
    res = evaluate_age_check(
        patient_exists=True,
        patient_age=12,
        candidate_medicine="Ciprofloxacin 500mg Tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.HIGH
    assert "conflicts with patient's age (12 years old)" in res.reason
    assert res.evidence is not None
    assert "Contraindicated in pediatric patients under 18 years old" in res.evidence


def test_3_age_conflict_causes_blocked_decision():
    """Verify that an age conflict produces a BLOCKED decision with recommended_medicine=None."""
    patient = Patient(id=1, patient_code="PAT-PED", age=6, sex="Male")
    c = ClinicalConstraint(
        id=1,
        medicine_name="Doxycycline 100mg Capsule",
        constraint_type="AGE",
        constraint_rule="Contraindicated in pediatric patients under 8 years old",
        severity="HIGH",
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Doxycycline 100mg Capsule",
    )
    cand = type(
        "Alt",
        (),
        {
            "source_medicine": "Doxycycline 100mg Capsule",
            "alternative_medicine": "Doxycycline 100mg Capsule",
            "alternative_ingredient": "Doxycycline",
        },
    )()

    decision = evaluate_substitution_lookup(
        req, [cand], patient=patient, clinical_constraints=[c]
    )

    assert decision.decision_status == DecisionStatus.BLOCKED
    assert decision.recommended_medicine is None
    assert decision.requires_human_confirmation is True


def test_4_severity_mapping_works():
    """Verify that severity maps correctly for AGE constraints."""
    c_crit = ClinicalConstraint(
        id=1,
        medicine_name="Med A",
        constraint_type="AGE",
        constraint_rule="Contraindicated under 18 years old",
        severity="CRITICAL",
    )
    res = evaluate_age_check(True, 10, "Med A", [c_crit])
    assert res.severity == RiskLevel.CRITICAL


def test_5_exact_medicine_matching():
    """Verify exact case-insensitive normalized matching for age constraints."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="  Ciprofloxacin 500mg Tablet  ",
        constraint_type="  AGE  ",
        constraint_rule="Contraindicated under 18 years old",
        severity="HIGH",
    )
    res = evaluate_age_check(
        patient_exists=True,
        patient_age=14,
        candidate_medicine="ciprofloxacin 500mg tablet",
        constraints=[c],
    )
    assert res.status == CheckStatus.FAIL


def test_6_substring_matching_does_not_trigger_rule():
    """Verify that substring medicine names do NOT trigger age constraint rules."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="Ciprofloxacin 500mg Tablet",
        constraint_type="AGE",
        constraint_rule="Contraindicated under 18 years old",
        severity="HIGH",
    )
    # Different medicine name
    res = evaluate_age_check(
        patient_exists=True,
        patient_age=14,
        candidate_medicine="Cipro",
        constraints=[],
    )
    assert res.status == CheckStatus.PASS


def test_7_missing_age_is_not_treated_as_safe():
    """Verify that a missing or None patient age is treated as a FAIL condition."""
    res = evaluate_age_check(
        patient_exists=True,
        patient_age=None,
        candidate_medicine="Ciprofloxacin 500mg Tablet",
        constraints=[],
    )
    assert res.status == CheckStatus.FAIL
    assert "Patient age is missing" in res.reason


def test_8_explainable_reason_and_evidence():
    """Verify that age check returns human-readable reason and evidence."""
    c = ClinicalConstraint(
        id=99,
        medicine_name="Doxycycline 100mg Capsule",
        constraint_type="AGE",
        constraint_rule="Contraindicated in pediatric patients under 8 years old",
        severity="HIGH",
        evidence_source="Synthetic prototype pediatric dataset ID 99",
    )
    res = evaluate_age_check(True, 5, "Doxycycline 100mg Capsule", [c])
    assert res.evidence is not None
    assert "Synthetic prototype pediatric dataset ID 99" in res.evidence
    assert "conflicts with patient's age (5 years old)" in res.reason


def test_9_pipeline_order_includes_all_6_checks():
    """Verify all 6 checks are evaluated in execution order."""
    patient = Patient(id=1, patient_code="PAT-0001", age=45, sex="Female")
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
        req, [cand], patient=patient, allergies=[], clinical_constraints=[]
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


def test_10_deterministic_age_evaluations():
    """Verify that identical inputs produce identical age decision outputs."""
    c = ClinicalConstraint(
        id=1,
        medicine_name="Med A",
        constraint_type="AGE",
        constraint_rule="Contraindicated under 18 years old",
        severity="HIGH",
    )
    res1 = evaluate_age_check(True, 15, "Med A", [c])
    res2 = evaluate_age_check(True, 15, "Med A", [c])
    assert res1.model_dump_json() == res2.model_dump_json()
