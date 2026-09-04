from datetime import date, timedelta
import pytest
from app.models.medication import PrescriptionMedication
from app.models.patient import Patient
from app.models.stock import MedicineStock
from app.schemas.substitution import (
    CheckStatus,
    DecisionStatus,
    RiskLevel,
    SubstitutionRequest,
)
from app.services.substitution_engine import (
    evaluate_stock_check,
    evaluate_substitution_lookup,
)


def test_1_available_stock_passes():
    """Verify that a valid non-expired available stock record passes stock check."""
    s = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-001",
        quantity_available=150,
        expiry_date=date.today() + timedelta(days=180),
        is_available=True,
        pharmacy_location="Main Shelf A-12",
    )
    res = evaluate_stock_check(
        candidate_medicine="Ampicillin 500mg Capsule", stock_records=[s]
    )
    assert res.status == CheckStatus.PASS
    assert "Usable stock is available" in res.reason
    assert res.evidence is not None
    evidence = res.evidence
    assert "BAT-001" in evidence
    assert "Main Shelf A-12" in evidence


def test_2_quantity_zero_fails():
    """Verify that a stock record with quantity_available == 0 fails stock check."""
    s = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-ZERO",
        quantity_available=0,
        expiry_date=date.today() + timedelta(days=180),
        is_available=True,
    )
    res = evaluate_stock_check(
        candidate_medicine="Ampicillin 500mg Capsule", stock_records=[s]
    )
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.HIGH
    assert "No usable stock is available" in res.reason


def test_3_is_available_false_fails():
    """Verify that a stock record with is_available == False fails stock check."""
    s = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-UNAVAIL",
        quantity_available=50,
        expiry_date=date.today() + timedelta(days=180),
        is_available=False,
    )
    res = evaluate_stock_check(
        candidate_medicine="Ampicillin 500mg Capsule", stock_records=[s]
    )
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.HIGH


def test_4_no_stock_record_fails():
    """Verify that 0 stock records returned fails stock check."""
    res = evaluate_stock_check(
        candidate_medicine="Ampicillin 500mg Capsule", stock_records=[]
    )
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.HIGH
    assert "No usable stock is available" in res.reason


def test_5_expired_stock_fails():
    """Verify that an expired stock record fails with an explicit expired stock reason."""
    s_expired = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-EXP",
        quantity_available=100,
        expiry_date=date.today() - timedelta(days=30),
        is_available=True,
    )
    res = evaluate_stock_check(
        candidate_medicine="Ampicillin 500mg Capsule", stock_records=[s_expired]
    )
    assert res.status == CheckStatus.FAIL
    assert "All available stock for the proposed alternative medicine is expired." in res.reason


def test_6_available_and_expired_batches_passes():
    """Verify that if one expired batch and one valid batch exist, the valid batch triggers PASS."""
    s_exp = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-EXP",
        quantity_available=100,
        expiry_date=date.today() - timedelta(days=30),
        is_available=True,
    )
    s_valid = MedicineStock(
        id=2,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-VALID",
        quantity_available=200,
        expiry_date=date.today() + timedelta(days=90),
        is_available=True,
    )
    res = evaluate_stock_check(
        candidate_medicine="Ampicillin 500mg Capsule",
        stock_records=[s_exp, s_valid],
    )
    assert res.status == CheckStatus.PASS
    assert res.evidence is not None
    assert "BAT-VALID" in res.evidence


def test_7_case_and_whitespace_normalization():
    """Verify case-insensitive and whitespace-normalized stock medicine matching."""
    s = MedicineStock(
        id=1,
        medicine_name="  Ampicillin 500mg Capsule  ",
        batch_code="BAT-001",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=100),
        is_available=True,
    )
    res = evaluate_stock_check(
        candidate_medicine="ampicillin 500mg capsule", stock_records=[s]
    )
    assert res.status == CheckStatus.PASS


def test_8_no_substring_matching():
    """Verify exact medicine matching without substring false positives."""
    res = evaluate_stock_check(
        candidate_medicine="Paracetamol", stock_records=[]
    )
    assert res.status == CheckStatus.FAIL


def test_9_missing_medicine_name_fails():
    """Verify missing candidate medicine name returns CheckStatus.FAIL with RiskLevel.HIGH."""
    res = evaluate_stock_check(candidate_medicine="", stock_records=[])
    assert res.status == CheckStatus.FAIL
    assert res.severity == RiskLevel.HIGH
    assert "Proposed alternative medicine name is missing" in res.reason


def test_10_pipeline_order_includes_all_9_checks():
    """Verify all 9 checks are evaluated in execution order."""
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
            "alternative_medicine": "Ampicillin 500mg Capsule",
            "alternative_ingredient": "Ampicillin",
        },
    )()
    stock = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-001",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=180),
        is_available=True,
    )
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
        stock_records=[stock],
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


def test_11_deterministic_stock_evaluations():
    """Verify that identical inputs produce identical stock decision outputs."""
    s = MedicineStock(
        id=1,
        medicine_name="Ampicillin 500mg Capsule",
        batch_code="BAT-001",
        quantity_available=100,
        expiry_date=date.today() + timedelta(days=100),
        is_available=True,
    )
    res1 = evaluate_stock_check("Ampicillin 500mg Capsule", [s])
    res2 = evaluate_stock_check("Ampicillin 500mg Capsule", [s])
    assert res1.model_dump_json() == res2.model_dump_json()
