import pytest
from app.db.session import SessionLocal
from app.models.allergy import Allergy
from app.models.patient import Patient
from app.repositories.allergy_repository import (
    get_patient_allergies,
    get_patient_by_id,
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
    evaluate_patient_allergy_check,
    evaluate_substitution_lookup,
)


def test_1_patient_with_no_allergies_passes():
    """Verify that a patient with 0 recorded allergies receives CheckStatus.PASS."""
    res = evaluate_patient_allergy_check(
        patient_exists=True,
        allergies=[],
        alternative_medicine="Cefalexin 500mg Capsule",
        alternative_ingredient="Cefalexin",
    )
    assert res.status == CheckStatus.PASS
    assert "No recorded allergy conflict was found" in res.reason


def test_2_patient_with_matching_allergy_fails_and_blocks():
    """Verify that a patient with a matching allergy receives CheckStatus.FAIL and BLOCKED decision status."""
    db = SessionLocal()
    try:
        # Patient PAT-0002 has severe PENICILLIN allergy
        patient = db.query(Patient).filter_by(patient_code="PAT-0002").first()
        assert patient is not None
        allergies = get_patient_allergies(db, patient.id)
        alts = get_active_alternatives_for_medicine(db, "Amoxicillin 500mg Capsule")

        req = SubstitutionRequest(
            patient_id=patient.id,
            prescription_id=1,
            prescription_medication_id=1,
            original_medicine="Amoxicillin 500mg Capsule",
        )
        decision = evaluate_substitution_lookup(req, alts, patient_exists=True, allergies=allergies)

        assert decision.decision_status == DecisionStatus.BLOCKED
        assert decision.recommended_medicine is None
        assert decision.requires_human_confirmation is True
        assert decision.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert "PENICILLIN" in decision.reason or "allergy" in decision.reason
    finally:
        db.close()


def test_3_patient_with_non_matching_allergy_passes():
    """Verify that a patient with a non-matching allergy (e.g., NSAID) passes for a Cefalexin alternative."""
    allergy = Allergy(id=1, patient_id=1, allergen="NSAID", reaction="HIVES", severity="MODERATE")
    res = evaluate_patient_allergy_check(
        patient_exists=True,
        allergies=[allergy],
        alternative_medicine="Cefalexin 500mg Capsule",
        alternative_ingredient="Cefalexin",
    )
    assert res.status == CheckStatus.PASS


def test_4_severe_allergy_conflict_maps_to_critical_risk():
    """Verify that SEVERE allergy records map to CRITICAL risk level."""
    allergy = Allergy(id=1, patient_id=1, allergen="PENICILLIN", reaction="ANAPHYLAXIS", severity="SEVERE")
    res = evaluate_patient_allergy_check(
        patient_exists=True,
        allergies=[allergy],
        alternative_medicine="Cefalexin 500mg Capsule",
        alternative_ingredient="Cefalexin",
    )
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.CRITICAL


def test_5_multiple_allergies_all_evaluated():
    """Verify that all allergies are evaluated and any conflict triggers FAIL."""
    a1 = Allergy(id=1, patient_id=1, allergen="MACROLIDE", reaction="RASH", severity="MILD")
    a2 = Allergy(id=2, patient_id=1, allergen="PENICILLIN", reaction="HIVES", severity="SEVERE")
    res = evaluate_patient_allergy_check(
        patient_exists=True,
        allergies=[a1, a2],
        alternative_medicine="Ampicillin 500mg Capsule",
        alternative_ingredient="Ampicillin",
    )
    assert res.status == CheckStatus.FAIL
    assert "PENICILLIN" in res.reason


def test_6_case_and_whitespace_normalization():
    """Verify case-insensitive and whitespace-normalized allergen matching."""
    allergy = Allergy(id=1, patient_id=1, allergen="  penicillin  ", severity="MODERATE")
    res = evaluate_patient_allergy_check(
        patient_exists=True,
        allergies=[allergy],
        alternative_medicine="AMOXICILLIN 500MG CAPSULE",
        alternative_ingredient="AMOXICILLIN",
    )
    assert res.status == CheckStatus.FAIL


def test_7_substring_matching_does_not_trigger_false_positive():
    """Verify that partial allergen substrings (e.g. 'Peni') do NOT trigger false positives for unrelated medicines."""
    allergy = Allergy(id=1, patient_id=1, allergen="Peni", severity="MODERATE")
    res = evaluate_patient_allergy_check(
        patient_exists=True,
        allergies=[allergy],
        alternative_medicine="Metformin 500mg Tablet",
        alternative_ingredient="Metformin",
    )
    assert res.status == CheckStatus.PASS


def test_8_missing_patient_handled_safely():
    """Verify that a missing/nonexistent patient ID returns CheckStatus.FAIL and is not treated as safe."""
    res = evaluate_patient_allergy_check(
        patient_exists=False,
        allergies=[],
        alternative_medicine="Cefalexin 500mg Capsule",
        alternative_ingredient="Cefalexin",
    )
    assert res.status == CheckStatus.FAIL
    assert "Patient record ID not found" in res.reason


def test_9_allergy_conflict_produces_blocked_decision_without_recommended_medicine():
    """Verify that an allergy conflict produces BLOCKED status and sets recommended_medicine to None."""
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Amoxicillin 500mg Capsule",
    )
    allergy = Allergy(id=1, patient_id=1, allergen="PENICILLIN", severity="SEVERE")
    alts = [
        type("Alt", (), {
            "source_medicine": "Amoxicillin 500mg Capsule",
            "alternative_medicine": "Cefalexin 500mg Capsule",
            "alternative_ingredient": "Cefalexin",
        })()
    ]

    decision = evaluate_substitution_lookup(req, alts, patient_exists=True, allergies=[allergy])

    assert decision.decision_status == DecisionStatus.BLOCKED
    assert decision.recommended_medicine is None
    assert decision.requires_human_confirmation is True
    assert "allergy" in decision.reason.lower()
