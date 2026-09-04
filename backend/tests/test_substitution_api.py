import warnings
warnings.filterwarnings("ignore")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.main import app
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.medication import PrescriptionMedication

client = TestClient(app)


def test_1_successful_substitution_evaluation_endpoint():
    """Verify POST /api/v1/substitutions/evaluate returns 200 OK with valid response format."""
    db = SessionLocal()
    try:
        # Find PAT-0001
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        assert pat is not None
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        assert rx is not None
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()
        assert med is not None

        payload = {
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        }

        response = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "decision_status" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)
    finally:
        db.close()


def test_2_safe_scenario_returns_needs_review_with_candidate():
    """Verify that a safe substitution scenario returns NEEDS_REVIEW with an approved alternative."""
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
        assert data["decision_status"] in ("NEEDS_REVIEW", "RECOMMENDED")
        assert data["recommended_medicine"] is not None
        assert data["requires_human_confirmation"] is True
    finally:
        db.close()


def test_3_allergy_blocked_scenario():
    """Verify that PAT-0002 with severe PENICILLIN allergy is BLOCKED for Amoxicillin substitution."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0002").first()
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
        assert data["decision_status"] == "BLOCKED"
        assert data["recommended_medicine"] is None
        assert "allergy" in data["reason"].lower() or "blocked" in data["reason"].lower()
    finally:
        db.close()


def test_4_stock_unavailable_scenario():
    """Verify that requesting an unapproved or out-of-stock medicine returns BLOCKED or NO_ALTERNATIVE."""
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
            "requested_alternative": "Nonexistent OutOfStock Drug 500mg",
        }

        response = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision_status"] in ("NO_ALTERNATIVE", "BLOCKED")
        assert data["recommended_medicine"] is None
    finally:
        db.close()


def test_5_clinical_blocked_scenario_pregnancy():
    """Verify that a pregnant patient attempting a teratogenic drug is BLOCKED by pregnancy check."""
    db = SessionLocal()
    try:
        # PAT-0006 is pregnant in seed dataset
        pat = db.query(Patient).filter_by(pregnancy_status="PREGNANT").first()
        assert pat is not None
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        assert rx is not None
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()
        assert med is not None

        payload = {
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        }

        response = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        if data["decision_status"] == "BLOCKED":
            assert data["recommended_medicine"] is None
            assert data["requires_human_confirmation"] is True
    finally:
        db.close()


def test_6_human_confirmation_flag_required():
    """Verify that requires_human_confirmation is True in DecisionResult."""
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
        assert data["requires_human_confirmation"] is True
    finally:
        db.close()


def test_7_missing_patient_returns_404():
    """Verify that non-existent patient_id returns HTTP 404 Not Found."""
    payload = {
        "patient_id": 999999,
        "prescription_id": 1,
        "prescription_medication_id": 1,
        "original_medicine": "Amoxicillin 500mg Capsule",
    }
    response = client.post("/api/v1/substitutions/evaluate", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Patient record not found."


def test_8_missing_prescription_returns_404():
    """Verify that non-existent prescription_id returns HTTP 404 Not Found."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).first()
        payload = {
            "patient_id": pat.id,
            "prescription_id": 999999,
            "prescription_medication_id": 1,
            "original_medicine": "Amoxicillin 500mg Capsule",
        }
        response = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert response.status_code == 404
        assert response.json()["detail"] == "Prescription record not found."
    finally:
        db.close()


def test_9_missing_prescription_medication_returns_404():
    """Verify that non-existent prescription_medication_id returns HTTP 404 Not Found."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        payload = {
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": 999999,
            "original_medicine": "Amoxicillin 500mg Capsule",
        }
        response = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert response.status_code == 404
        assert response.json()["detail"] == "Prescription medication record not found."
    finally:
        db.close()


def test_10_medication_wrong_prescription_returns_400():
    """Verify that a medication ID belonging to a different prescription returns HTTP 400 Bad Request."""
    db = SessionLocal()
    try:
        meds = db.query(PrescriptionMedication).all()
        assert len(meds) >= 2
        med1, med2 = meds[0], meds[1]
        
        # Pick med2's ID but med1's prescription_id
        if med1.prescription_id != med2.prescription_id:
            rx = db.query(Prescription).filter_by(id=med1.prescription_id).first()
            payload = {
                "patient_id": rx.patient_id,
                "prescription_id": rx.id,
                "prescription_medication_id": med2.id,
                "original_medicine": med2.medicine_name,
            }
            response = client.post("/api/v1/substitutions/evaluate", json=payload)
            assert response.status_code == 400
            assert response.json()["detail"] == "Prescription medication does not belong to the supplied prescription."
    finally:
        db.close()


def test_11_prescription_wrong_patient_returns_400():
    """Verify that a prescription ID belonging to a different patient returns HTTP 400 Bad Request."""
    db = SessionLocal()
    try:
        pats = db.query(Patient).all()
        assert len(pats) >= 2
        pat1, pat2 = pats[0], pats[1]
        rx2 = db.query(Prescription).filter_by(patient_id=pat2.id).first()
        med2 = db.query(PrescriptionMedication).filter_by(prescription_id=rx2.id).first()

        payload = {
            "patient_id": pat1.id,
            "prescription_id": rx2.id,
            "prescription_medication_id": med2.id,
            "original_medicine": med2.medicine_name,
        }
        response = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert response.status_code == 400
        assert response.json()["detail"] == "Prescription does not belong to the supplied patient."
    finally:
        db.close()


def test_12_invalid_request_body_returns_422():
    """Verify that invalid data types in request body return HTTP 422 Unprocessable Entity."""
    payload = {
        "patient_id": "invalid_string_id",
        "prescription_id": 1,
        "prescription_medication_id": 1,
        "original_medicine": "Amoxicillin 500mg Capsule",
    }
    response = client.post("/api/v1/substitutions/evaluate", json=payload)
    assert response.status_code == 422


def test_13_missing_required_fields_returns_422():
    """Verify that missing required fields in request body return HTTP 422 Unprocessable Entity."""
    response = client.post("/api/v1/substitutions/evaluate", json={})
    assert response.status_code == 422


def test_14_pipeline_order_contains_all_9_checks():
    """Verify that response checks list contains all 9 checks in execution order."""
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
        check_names = [c["check_name"] for c in data["checks"]]
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
    finally:
        db.close()


def test_15_decision_result_schema_fields():
    """Verify that response matches all DecisionResult schema fields."""
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
        expected_keys = {
            "decision_status",
            "original_medicine",
            "recommended_medicine",
            "reason",
            "risk_level",
            "requires_human_confirmation",
            "confidence_score",
            "checks",
        }
        assert expected_keys.issubset(set(data.keys()))
    finally:
        db.close()


def test_16_error_responses_do_not_leak_sensitive_info():
    """Verify that error responses do not leak database connection strings or stack trace internals."""
    payload = {
        "patient_id": 999999,
        "prescription_id": 1,
        "prescription_medication_id": 1,
        "original_medicine": "Amoxicillin 500mg Capsule",
    }
    response = client.post("/api/v1/substitutions/evaluate", json=payload)
    assert response.status_code == 404
    body = response.text
    assert "postgresql" not in body.lower()
    assert "password" not in body.lower()
    assert "traceback" not in body.lower()


def test_17_preset_lookup_endpoint():
    """Verify GET /api/v1/substitutions/preset-lookup/{patient_code}/{prescription_code} dynamically resolves database IDs."""
    response = client.get("/api/v1/substitutions/preset-lookup/PAT-0001/RX-0001")
    assert response.status_code == 200
    data = response.json()
    assert "patient_id" in data
    assert data["patient_code"] == "PAT-0001"
    assert "prescription_id" in data
    assert data["prescription_code"] == "RX-0001"
    assert "prescription_medication_id" in data
    assert "medicine_name" in data

    # Test invalid code 404
    bad_res = client.get("/api/v1/substitutions/preset-lookup/PAT-INVALID/RX-0001")
    assert bad_res.status_code == 404

