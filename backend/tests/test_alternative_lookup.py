import pytest
from app.db.session import SessionLocal
from app.models.alternative import MedicineAlternative
from app.repositories.alternative_repository import (
    get_active_alternatives_for_medicine,
)
from app.schemas.substitution import (
    CheckStatus,
    DecisionStatus,
    SubstitutionRequest,
)
from app.services.substitution_engine import (
    evaluate_approved_alternative_check,
    evaluate_substitution_lookup,
)


def test_1_active_source_medicine_returns_alternatives():
    """Verify that looking up an existing active medicine returns candidate alternatives."""
    db = SessionLocal()
    try:
        results = get_active_alternatives_for_medicine(db, "Amoxicillin 500mg Capsule")
        assert len(results) >= 2
        alt_names = [r.alternative_medicine for r in results]
        assert "Cefalexin 500mg Capsule" in alt_names
        assert "Ampicillin 500mg Capsule" in alt_names
    finally:
        db.close()


def test_2_inactive_alternative_is_excluded():
    """Verify that inactive alternatives (is_active=False) are excluded from repository lookup."""
    db = SessionLocal()
    try:
        # Insert temporary inactive alternative
        inactive_alt = MedicineAlternative(
            source_medicine="TestMed Inactive 100mg",
            alternative_medicine="TestMed Candidate 100mg",
            source_ingredient="TestIngred",
            alternative_ingredient="TestIngred",
            equivalence_type="Therapeutic Equivalent",
            is_active=False,
        )
        db.add(inactive_alt)
        db.commit()

        results = get_active_alternatives_for_medicine(db, "TestMed Inactive 100mg")
        assert len(results) == 0

        # Clean up
        db.delete(inactive_alt)
        db.commit()
    finally:
        db.close()


def test_3_unknown_medicine_returns_no_alternatives():
    """Verify that searching for an unknown medicine returns an empty list."""
    db = SessionLocal()
    try:
        results = get_active_alternatives_for_medicine(db, "Unknown Nonexistent Medicine XYZ")
        assert len(results) == 0
    finally:
        db.close()


def test_4_case_normalization():
    """Verify exact case-insensitive normalized matching."""
    db = SessionLocal()
    try:
        res_lower = get_active_alternatives_for_medicine(db, "amoxicillin 500mg capsule")
        res_upper = get_active_alternatives_for_medicine(db, "AMOXICILLIN 500MG CAPSULE")
        res_mixed = get_active_alternatives_for_medicine(db, "  Amoxicillin 500mg Capsule  ")

        assert len(res_lower) == len(res_upper) == len(res_mixed)
        assert len(res_lower) >= 2
    finally:
        db.close()


def test_5_substring_and_fuzzy_matching_does_not_occur():
    """Verify that partial or substring searches (e.g., 'Amox') do NOT return matches."""
    db = SessionLocal()
    try:
        results_partial = get_active_alternatives_for_medicine(db, "Amox")
        results_prefix = get_active_alternatives_for_medicine(db, "Amoxicillin 500mg")

        assert len(results_partial) == 0
        assert len(results_prefix) == 0
    finally:
        db.close()


def test_6_multiple_active_alternatives_returned_deterministically():
    """Verify multiple active alternatives are returned in deterministic alphabetical order."""
    db = SessionLocal()
    try:
        results = get_active_alternatives_for_medicine(db, "Amoxicillin 500mg Capsule")
        assert len(results) >= 2
        names = [r.alternative_medicine for r in results]
        assert names == sorted(names)
    finally:
        db.close()


def test_7_no_alternative_decision_status():
    """Verify that a request with no active alternatives produces NO_ALTERNATIVE decision status and recommended_medicine=None."""
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Nonexistent Medicine 999mg",
    )
    decision = evaluate_substitution_lookup(req, candidates=[])

    assert decision.decision_status == DecisionStatus.NO_ALTERNATIVE
    assert decision.recommended_medicine is None
    assert decision.requires_human_confirmation is False


def test_8_no_alternative_explainable_reason():
    """Verify no-alternative decision contains explainable human-readable reason."""
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Unknown Medicine",
    )
    decision = evaluate_substitution_lookup(req, candidates=[])

    assert decision.reason == "No active approved alternative was found for the requested medicine."


def test_9_no_alternative_checklist_entry():
    """Verify no-alternative decision contains check_name='approved_alternative' with status=FAIL."""
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Unknown Medicine",
    )
    decision = evaluate_substitution_lookup(req, candidates=[])

    assert len(decision.checks) == 1
    chk = decision.checks[0]
    assert chk.check_name == "approved_alternative"
    assert chk.status == CheckStatus.FAIL
    assert chk.reason == "No active approved alternative was found for the requested medicine."
