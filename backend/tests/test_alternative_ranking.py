"""Step 3E - Decision Ranking and Best Alternative Selection Test Suite.

Comprehensive tests for deterministic candidate alternative evaluation, safety-first filtering,
priority-based candidate ranking, explainability, API integration, and edge cases.
"""

from datetime import date, timedelta
import json
import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.allergy import Allergy
from app.models.alternative import MedicineAlternative
from app.models.clinical_constraint import ClinicalConstraint
from app.models.medication import PrescriptionMedication
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.stock import MedicineStock
from app.schemas.substitution import (
    CheckStatus,
    DecisionStatus,
    RiskLevel,
    SubstitutionRequest,
)
from app.services.alternative_ranking import (
    CandidateEvaluation,
    evaluate_single_candidate,
    rank_and_select_candidate,
)
from app.services.substitution_engine import evaluate_substitution_lookup

client = TestClient(app)


def _mock_patient(age=30):
    return Patient(id=1, patient_code="PAT-0001", age=age, sex="Male")


def _mock_med(medicine_name="Amoxicillin 500mg Capsule"):
    return PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name=medicine_name,
        active_ingredient="Amoxicillin",
        dose="500mg",
        frequency="TID",
    )


def test_1_one_safe_candidate_selected():
    """Verify that when one safe candidate exists, it is recommended."""
    patient = _mock_patient()
    med = _mock_med()
    cand = MedicineAlternative(
        id=1,
        source_medicine="Amoxicillin 500mg Capsule",
        alternative_medicine="Cefalexin 500mg Capsule",
        source_ingredient="Amoxicillin",
        alternative_ingredient="Cefalexin",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    stock = MedicineStock(
        id=1,
        medicine_name="Cefalexin 500mg Capsule",
        batch_code="BAT-01",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Amoxicillin 500mg Capsule",
    )

    result = evaluate_substitution_lookup(
        request=req,
        candidates=[cand],
        patient=patient,
        prescribed_medication=med,
        prescribed_medications=[med],
        stock_records=[stock],
    )

    assert result.decision_status == DecisionStatus.RECOMMENDED
    assert result.recommended_medicine == "Cefalexin 500mg Capsule"
    assert result.requires_human_confirmation is True


def test_2_multiple_safe_candidates_deterministic_selection():
    """Verify deterministic ranking selects the top-ranked safe candidate."""
    patient = _mock_patient()
    med = _mock_med()
    cand_a = MedicineAlternative(
        id=1,
        source_medicine="Amoxicillin 500mg Capsule",
        alternative_medicine="Ampicillin 500mg Capsule",
        source_ingredient="Amoxicillin",
        alternative_ingredient="Ampicillin",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    cand_b = MedicineAlternative(
        id=2,
        source_medicine="Amoxicillin 500mg Capsule",
        alternative_medicine="Cefalexin 500mg Capsule",
        source_ingredient="Amoxicillin",
        alternative_ingredient="Cefalexin",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )

    # Cand A has 50 units stock, Cand B has 200 units stock
    stock_a = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-A",
        quantity_available=50,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    stock_b = MedicineStock(
        id=2,
        medicine_name="Cefalexin 500mg Capsule",
        batch_code="BAT-B",
        quantity_available=200,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )

    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Amoxicillin 500mg Capsule",
    )

    eval_a = evaluate_single_candidate(
        request=req,
        candidate=cand_a,
        all_candidates=[cand_a, cand_b],
        patient=patient,
        prescribed_medication=med,
        prescribed_medications=[med],
        stock_records=[stock_a],
    )
    eval_b = evaluate_single_candidate(
        request=req,
        candidate=cand_b,
        all_candidates=[cand_a, cand_b],
        patient=patient,
        prescribed_medication=med,
        prescribed_medications=[med],
        stock_records=[stock_b],
    )

    result = rank_and_select_candidate(req, [eval_a, eval_b])

    # Cand B has greater stock availability (200 > 50), so Priority 3 selects Cefalexin
    assert result.decision_status == DecisionStatus.RECOMMENDED
    assert result.recommended_medicine == "Cefalexin 500mg Capsule"


def test_3_candidate_with_allergy_failure_excluded():
    """Verify a candidate failing allergy check is strictly excluded from recommendation."""
    cand = MedicineAlternative(
        id=1,
        source_medicine="Amoxicillin 500mg Capsule",
        alternative_medicine="Ampicillin 500mg Capsule",
        source_ingredient="Amoxicillin",
        alternative_ingredient="Ampicillin",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    allergy = Allergy(
        id=1,
        patient_id=1,
        allergen="AMPICILLIN",
        severity="HIGH",
    )
    stock = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-01",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Amoxicillin 500mg Capsule",
    )

    result = evaluate_substitution_lookup(
        request=req,
        candidates=[cand],
        patient_exists=True,
        allergies=[allergy],
        stock_records=[stock],
    )

    assert result.decision_status == DecisionStatus.BLOCKED
    assert result.recommended_medicine is None


def test_4_candidate_with_renal_failure_excluded():
    """Verify candidate failing RENAL clinical constraint is excluded."""
    patient = Patient(id=1, patient_code="PAT-0001", age=40, renal_status="MODERATE_IMPAIRMENT")
    cand = MedicineAlternative(
        id=1,
        source_medicine="Metformin 500mg Tablet",
        alternative_medicine="Gliclazide 80mg Tablet",
        source_ingredient="Metformin",
        alternative_ingredient="Gliclazide",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    constraint = ClinicalConstraint(
        id=1,
        constraint_type="RENAL",
        constraint_rule="Contraindicated in moderate_impairment renal failure",
        severity="HIGH",
        is_active=True,
    )
    stock = MedicineStock(
        id=1,
        medicine_name="Gliclazide 80mg Tablet",
        batch_code="BAT-01",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Metformin 500mg Tablet",
    )

    result = evaluate_substitution_lookup(
        request=req,
        candidates=[cand],
        patient=patient,
        clinical_constraints=[constraint],
        stock_records=[stock],
    )

    assert result.decision_status == DecisionStatus.BLOCKED
    assert result.recommended_medicine is None


def test_5_candidate_with_hepatic_failure_excluded():
    """Verify candidate failing HEPATIC clinical constraint is excluded."""
    patient = Patient(id=1, patient_code="PAT-0001", age=40, hepatic_status="SEVERE_IMPAIRMENT")
    cand = MedicineAlternative(
        id=1,
        source_medicine="Paracetamol 500mg Tablet",
        alternative_medicine="StatMed 20mg Tablet",
        source_ingredient="Paracetamol",
        alternative_ingredient="StatMed",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    constraint = ClinicalConstraint(
        id=1,
        constraint_type="HEPATIC",
        constraint_rule="Avoid in severe_impairment hepatic failure",
        severity="CRITICAL",
        is_active=True,
    )
    stock = MedicineStock(
        id=1,
        medicine_name="StatMed 20mg Tablet",
        batch_code="BAT-01",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Paracetamol 500mg Tablet",
    )

    result = evaluate_substitution_lookup(
        request=req,
        candidates=[cand],
        patient=patient,
        clinical_constraints=[constraint],
        stock_records=[stock],
    )

    assert result.decision_status == DecisionStatus.BLOCKED
    assert result.recommended_medicine is None


def test_6_candidate_with_pregnancy_failure_excluded():
    """Verify candidate failing PREGNANCY constraint is excluded."""
    patient = Patient(id=1, patient_code="PAT-0001", age=30, pregnancy_status="PREGNANT")
    cand = MedicineAlternative(
        id=1,
        source_medicine="Ramipril 5mg Tablet",
        alternative_medicine="Enalapril 5mg Tablet",
        source_ingredient="Ramipril",
        alternative_ingredient="Enalapril",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    constraint = ClinicalConstraint(
        id=1,
        constraint_type="PREGNANCY",
        constraint_rule="Contraindicated in pregnancy",
        severity="CRITICAL",
        is_active=True,
    )
    stock = MedicineStock(
        id=1,
        medicine_name="Enalapril 5mg Tablet",
        batch_code="BAT-01",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Ramipril 5mg Tablet",
    )

    result = evaluate_substitution_lookup(
        request=req,
        candidates=[cand],
        patient=patient,
        clinical_constraints=[constraint],
        stock_records=[stock],
    )

    assert result.decision_status == DecisionStatus.BLOCKED
    assert result.recommended_medicine is None


def test_7_candidate_with_age_failure_excluded():
    """Verify candidate failing AGE constraint is excluded."""
    patient = Patient(id=1, patient_code="PAT-0001", age=12)
    cand = MedicineAlternative(
        id=1,
        source_medicine="Ciprofloxacin 500mg Tablet",
        alternative_medicine="Levofloxacin 500mg Tablet",
        source_ingredient="Ciprofloxacin",
        alternative_ingredient="Levofloxacin",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    constraint = ClinicalConstraint(
        id=1,
        constraint_type="AGE",
        constraint_rule="Not recommended for patients under 18 years old",
        severity="HIGH",
        is_active=True,
    )
    stock = MedicineStock(
        id=1,
        medicine_name="Levofloxacin 500mg Tablet",
        batch_code="BAT-01",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Ciprofloxacin 500mg Tablet",
    )

    result = evaluate_substitution_lookup(
        request=req,
        candidates=[cand],
        patient=patient,
        clinical_constraints=[constraint],
        stock_records=[stock],
    )

    assert result.decision_status == DecisionStatus.BLOCKED
    assert result.recommended_medicine is None


def test_8_candidate_with_drug_interaction_failure_excluded():
    """Verify candidate failing DRUG_INTERACTION check is excluded."""
    patient = Patient(id=1, patient_code="PAT-0001", age=40)
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Warfarin 5mg Tablet",
        active_ingredient="Warfarin",
        dose="5mg",
        frequency="QD",
    )
    cand = MedicineAlternative(
        id=1,
        source_medicine="Ibuprofen 400mg Tablet",
        alternative_medicine="Naproxen 250mg Tablet",
        source_ingredient="Ibuprofen",
        alternative_ingredient="Naproxen",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    constraint = ClinicalConstraint(
        id=1,
        constraint_type="DRUG_INTERACTION",
        constraint_rule="Severe interaction with warfarin",
        severity="CRITICAL",
        is_active=True,
    )
    stock = MedicineStock(
        id=1,
        medicine_name="Naproxen 250mg Tablet",
        batch_code="BAT-01",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Ibuprofen 400mg Tablet",
    )

    result = evaluate_substitution_lookup(
        request=req,
        candidates=[cand],
        patient=patient,
        clinical_constraints=[constraint],
        prescribed_medication=med,
        prescribed_medications=[med],
        stock_records=[stock],
    )

    assert result.decision_status == DecisionStatus.BLOCKED
    assert result.recommended_medicine is None


def test_9_candidate_with_dosage_failure_excluded():
    """Verify candidate failing DOSAGE constraint is excluded."""
    patient = Patient(id=1, patient_code="PAT-0001", age=40)
    med = PrescriptionMedication(
        id=1,
        prescription_id=1,
        medicine_name="Paracetamol 1000mg Tablet",
        active_ingredient="Paracetamol",
        dose="1000mg",
        frequency="QID",
    )
    cand = MedicineAlternative(
        id=1,
        source_medicine="Paracetamol 1000mg Tablet",
        alternative_medicine="Paracetamol Extra 1000mg Tablet",
        source_ingredient="Paracetamol",
        alternative_ingredient="Paracetamol",
        equivalence_type="Pharmaceutical Equivalent",
        is_active=True,
    )
    constraint = ClinicalConstraint(
        id=1,
        constraint_type="DOSAGE",
        constraint_rule="Maximum daily dose is 3000mg",
        severity="HIGH",
        is_active=True,
    )
    stock = MedicineStock(
        id=1,
        medicine_name="Paracetamol Extra 1000mg Tablet",
        batch_code="BAT-01",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Paracetamol 1000mg Tablet",
    )

    result = evaluate_substitution_lookup(
        request=req,
        candidates=[cand],
        patient=patient,
        clinical_constraints=[constraint],
        prescribed_medication=med,
        prescribed_medications=[med],
        stock_records=[stock],
    )

    assert result.decision_status == DecisionStatus.BLOCKED
    assert result.recommended_medicine is None


def test_10_candidate_with_unavailable_zero_expired_stock_excluded():
    """Verify candidates with expired, zero, or unavailable stock are excluded."""
    cand = MedicineAlternative(
        id=1,
        source_medicine="Amoxicillin 500mg Capsule",
        alternative_medicine="Ampicillin 500mg Capsule",
        source_ingredient="Amoxicillin",
        alternative_ingredient="Ampicillin",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    stock_zero = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-ZERO",
        quantity_available=0,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Amoxicillin 500mg Capsule",
    )

    result = evaluate_substitution_lookup(
        request=req,
        candidates=[cand],
        patient_exists=True,
        stock_records=[stock_zero],
    )

    assert result.decision_status == DecisionStatus.BLOCKED
    assert result.recommended_medicine is None


def test_11_safe_candidate_preferred_over_unsafe_candidate():
    """Verify safe candidate is selected over an unsafe candidate even if unsafe candidate has higher stock."""
    patient = _mock_patient()
    med = _mock_med()
    unsafe_cand = MedicineAlternative(
        id=1,
        source_medicine="Amoxicillin 500mg Capsule",
        alternative_medicine="Ampicillin 500mg Capsule",
        source_ingredient="Amoxicillin",
        alternative_ingredient="Ampicillin",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    safe_cand = MedicineAlternative(
        id=2,
        source_medicine="Amoxicillin 500mg Capsule",
        alternative_medicine="Cefalexin 500mg Capsule",
        source_ingredient="Amoxicillin",
        alternative_ingredient="Cefalexin",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )

    allergy = Allergy(
        id=1,
        patient_id=1,
        allergen="AMPICILLIN",
        severity="HIGH",
    )

    stock_unsafe = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-UNSAFE",
        quantity_available=500,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    stock_safe = MedicineStock(
        id=2,
        medicine_name="Cefalexin 500mg Capsule",
        batch_code="BAT-SAFE",
        quantity_available=20,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )

    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Amoxicillin 500mg Capsule",
    )

    eval_unsafe = evaluate_single_candidate(
        request=req,
        candidate=unsafe_cand,
        all_candidates=[unsafe_cand, safe_cand],
        patient=patient,
        allergies=[allergy],
        prescribed_medication=med,
        prescribed_medications=[med],
        stock_records=[stock_unsafe],
    )
    eval_safe = evaluate_single_candidate(
        request=req,
        candidate=safe_cand,
        all_candidates=[unsafe_cand, safe_cand],
        patient=patient,
        allergies=[allergy],
        prescribed_medication=med,
        prescribed_medications=[med],
        stock_records=[stock_safe],
    )

    result = rank_and_select_candidate(req, [eval_unsafe, eval_safe])

    assert result.decision_status == DecisionStatus.RECOMMENDED
    assert result.recommended_medicine == "Cefalexin 500mg Capsule"


def test_12_multiple_safe_candidates_produce_deterministic_selection():
    """Verify that multiple safe candidates with identical stock rank deterministically by name / ID."""
    patient = _mock_patient()
    med = _mock_med("Med Orig")
    cand_1 = MedicineAlternative(
        id=1,
        source_medicine="Med Orig",
        alternative_medicine="BetaMed 500mg",
        source_ingredient="Ing",
        alternative_ingredient="IngB",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    cand_2 = MedicineAlternative(
        id=2,
        source_medicine="Med Orig",
        alternative_medicine="AlphaMed 500mg",
        source_ingredient="Ing",
        alternative_ingredient="IngA",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )

    stock_1 = MedicineStock(
        id=1,
        medicine_name="BetaMed 500mg",
        batch_code="B1",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    stock_2 = MedicineStock(
        id=2,
        medicine_name="AlphaMed 500mg",
        batch_code="B2",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )

    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Med Orig",
    )

    eval_1 = evaluate_single_candidate(
        req, cand_1, [cand_1, cand_2],
        patient=patient, prescribed_medication=med, prescribed_medications=[med], stock_records=[stock_1]
    )
    eval_2 = evaluate_single_candidate(
        req, cand_2, [cand_1, cand_2],
        patient=patient, prescribed_medication=med, prescribed_medications=[med], stock_records=[stock_2]
    )

    # Alphabetical order: AlphaMed (Priority 4) comes before BetaMed
    result_a = rank_and_select_candidate(req, [eval_1, eval_2])
    result_b = rank_and_select_candidate(req, [eval_2, eval_1])

    assert result_a.recommended_medicine == "AlphaMed 500mg"
    assert result_b.recommended_medicine == "AlphaMed 500mg"


def test_13_all_candidates_blocked_returns_no_recommendation():
    """Verify that when all candidates fail safety checks, decision status is BLOCKED and recommended_medicine is None."""
    cand = MedicineAlternative(
        id=1,
        source_medicine="Amoxicillin 500mg Capsule",
        alternative_medicine="Ampicillin 500mg Capsule",
        source_ingredient="Amoxicillin",
        alternative_ingredient="Ampicillin",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    stock_zero = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-ZERO",
        quantity_available=0,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Amoxicillin 500mg Capsule",
    )

    result = evaluate_substitution_lookup(req, [cand], stock_records=[stock_zero])

    assert result.decision_status == DecisionStatus.BLOCKED
    assert result.recommended_medicine is None
    assert result.requires_human_confirmation is True
    assert "All 1 approved candidate alternative(s) failed safety evaluation" in result.reason


def test_14_no_approved_candidates_preserves_no_alternative_behavior():
    """Verify NO_ALTERNATIVE decision when no approved alternatives exist."""
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Nonexistent Med 999",
    )
    result = evaluate_substitution_lookup(req, candidates=[])

    assert result.decision_status == DecisionStatus.NO_ALTERNATIVE
    assert result.recommended_medicine is None
    assert result.requires_human_confirmation is False
    assert result.reason == "No active approved alternative was found for the requested medicine."
    assert len(result.checks) == 1
    assert result.checks[0].check_name == "approved_alternative"
    assert result.checks[0].status == CheckStatus.FAIL


def test_15_ranking_tie_breaker_is_deterministic_id():
    """Verify Priority 5 ID tie-breaker when safety, risk, stock, and name are identical."""
    patient = _mock_patient()
    med = _mock_med("Med Orig")
    cand_1 = MedicineAlternative(
        id=10,
        source_medicine="Med Orig",
        alternative_medicine="SameMed 500mg",
        source_ingredient="Ing",
        alternative_ingredient="IngS",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    cand_2 = MedicineAlternative(
        id=5,
        source_medicine="Med Orig",
        alternative_medicine="SameMed 500mg",
        source_ingredient="Ing",
        alternative_ingredient="IngS",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )

    stock = MedicineStock(
        id=1,
        medicine_name="SameMed 500mg",
        batch_code="B1",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )

    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Med Orig",
    )

    eval_1 = evaluate_single_candidate(
        req, cand_1, [cand_1, cand_2],
        patient=patient, prescribed_medication=med, prescribed_medications=[med], stock_records=[stock]
    )
    eval_2 = evaluate_single_candidate(
        req, cand_2, [cand_1, cand_2],
        patient=patient, prescribed_medication=med, prescribed_medications=[med], stock_records=[stock]
    )

    # ID 5 comes before ID 10
    result = rank_and_select_candidate(req, [eval_1, eval_2])
    assert result.decision_status == DecisionStatus.RECOMMENDED
    assert result.recommended_medicine == "SameMed 500mg"


def test_16_api_returns_selected_candidate_correctly():
    """Verify POST /api/v1/substitutions/evaluate endpoint returns 200 OK with recommended candidate."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        payload = {
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        }

        response = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision_status"] in ("RECOMMENDED", "NEEDS_REVIEW")
        assert data["recommended_medicine"] is not None
    finally:
        db.close()


def test_17_repeated_identical_requests_return_identical_json():
    """Verify deterministic JSON repeatability for identical requests."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        payload = {
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        }

        res1 = client.post("/api/v1/substitutions/evaluate", json=payload)
        res2 = client.post("/api/v1/substitutions/evaluate", json=payload)

        assert res1.status_code == 200
        assert res2.status_code == 200
        assert res1.text == res2.text
    finally:
        db.close()


def test_18_existing_explainability_evidence_preserved():
    """Verify evidence and check items are retained in decision result."""
    cand = MedicineAlternative(
        id=1,
        source_medicine="Amoxicillin 500mg Capsule",
        alternative_medicine="Cefalexin 500mg Capsule",
        source_ingredient="Amoxicillin",
        alternative_ingredient="Cefalexin",
        equivalence_type="Therapeutic Equivalent",
        is_active=True,
    )
    stock = MedicineStock(
        id=1,
        medicine_name="Cefalexin 500mg Capsule",
        batch_code="BAT-888",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Amoxicillin 500mg Capsule",
    )

    result = evaluate_substitution_lookup(
        request=req,
        candidates=[cand],
        patient_exists=True,
        stock_records=[stock],
    )

    assert len(result.checks) == 9
    check_names = [c.check_name for c in result.checks]
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
    stock_chk = [c for c in result.checks if c.check_name == "stock"][0]
    assert stock_chk.evidence is not None
    assert "BAT-888" in stock_chk.evidence


def test_19_no_sensitive_information_leaked():
    """Verify that response payload does not leak DB passwords, stack traces, or credentials."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        payload = {
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        }

        res = client.post("/api/v1/substitutions/evaluate", json=payload)
        json_str = res.text.lower()

        assert "password" not in json_str
        assert "secret" not in json_str
        assert "traceback" not in json_str
        assert "sqlalchemy" not in json_str
    finally:
        db.close()


def test_20_missing_invalid_input_safely_handled():
    """Verify 404 NOT FOUND for invalid patient ID and 422 for missing required fields."""
    # Invalid patient ID
    payload_invalid_pat = {
        "patient_id": 999999,
        "prescription_id": 1,
        "prescription_medication_id": 1,
        "original_medicine": "Amoxicillin 500mg Capsule",
    }
    res_404 = client.post("/api/v1/substitutions/evaluate", json=payload_invalid_pat)
    assert res_404.status_code == 404

    # Missing required field patient_id
    payload_missing = {
        "prescription_id": 1,
        "prescription_medication_id": 1,
        "original_medicine": "Amoxicillin 500mg Capsule",
    }
    res_422 = client.post("/api/v1/substitutions/evaluate", json=payload_missing)
    assert res_422.status_code == 422
