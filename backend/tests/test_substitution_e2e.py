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
from scripts.seed_data import seed_synthetic_data

client = TestClient(app)


def test_e2e_scenario_a_safe_path():
    """Scenario A E2E: Safe substitution request returns HTTP 200 with candidates and NEEDS_REVIEW/RECOMMENDED."""
    db: Session = SessionLocal()
    try:
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
        assert data["decision_status"] in ("NEEDS_REVIEW", "RECOMMENDED")
        assert data["recommended_medicine"] is not None
        assert data["requires_human_confirmation"] is True
        assert 0.0 <= data["confidence_score"] <= 1.0

        for check in data["checks"]:
            assert "check_name" in check
            assert "status" in check
            assert "reason" in check
            assert "severity" in check
    finally:
        db.close()


def test_e2e_scenario_b_allergy_block():
    """Scenario B E2E: Patient PAT-0002 with severe PENICILLIN allergy is BLOCKED for Amoxicillin substitution."""
    db: Session = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0002").first()
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
        assert data["decision_status"] == "BLOCKED"
        assert data["recommended_medicine"] is None
        assert data["risk_level"] in ("HIGH", "CRITICAL")

        allergy_checks = [c for c in data["checks"] if c["check_name"] == "allergy"]
        assert len(allergy_checks) > 0
        assert allergy_checks[0]["status"] == "FAIL"
        assert "PENICILLIN" in allergy_checks[0]["reason"].upper()
    finally:
        db.close()


def test_e2e_scenario_c_stock_failure():
    """Scenario C E2E: Alternative with zero stock (Metformin -> Gliclazide) returns BLOCKED with failed stock check."""
    db: Session = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0005").first()
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
            "requested_alternative": "Gliclazide 80mg Tablet",
        }

        response = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision_status"] in ("BLOCKED", "NO_ALTERNATIVE")
        assert data["recommended_medicine"] is None

        stock_checks = [c for c in data["checks"] if c["check_name"] == "stock"]
        assert len(stock_checks) > 0
        assert stock_checks[0]["status"] == "FAIL"
        assert "stock" in stock_checks[0]["reason"].lower()
    finally:
        db.close()


def test_e2e_scenario_d_clinical_block_pregnancy():
    """Scenario D E2E: Teratogenic drug contraindication for pregnant patient (PAT-0003) returns BLOCKED."""
    db: Session = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0003").first()
        assert pat is not None
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        assert rx is not None
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()
        assert med is not None

        payload = {
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": "Losartan 50mg Tablet",
            "requested_alternative": "Valsartan 80mg Tablet",
        }

        response = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision_status"] == "BLOCKED"
        assert data["recommended_medicine"] is None

        preg_checks = [c for c in data["checks"] if c["check_name"] == "pregnancy"]
        assert len(preg_checks) > 0
        assert preg_checks[0]["status"] == "FAIL"
        assert "pregnancy" in preg_checks[0]["reason"].lower() or "contraindicated" in preg_checks[0]["reason"].lower()
    finally:
        db.close()


def test_e2e_scenario_e_human_review_required():
    """Scenario E E2E: Valid candidate alternative requires human confirmation (requires_human_confirmation=True)."""
    db: Session = SessionLocal()
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
        assert data["decision_status"] in ("NEEDS_REVIEW", "RECOMMENDED")
    finally:
        db.close()


def test_e2e_pipeline_order_verification():
    """Verify that returned check list preserves exact 9-check pipeline execution order."""
    db: Session = SessionLocal()
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
        expected_order = [
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
        assert check_names == expected_order
    finally:
        db.close()


def test_e2e_decision_result_contract_validation():
    """Verify response strictly conforms to DecisionResult contract schema."""
    db: Session = SessionLocal()
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

        assert data["decision_status"] in ("RECOMMENDED", "BLOCKED", "NO_ALTERNATIVE", "NEEDS_REVIEW")
        assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert isinstance(data["requires_human_confirmation"], bool)
        assert isinstance(data["confidence_score"], float)
        assert 0.0 <= data["confidence_score"] <= 1.0

        for check in data["checks"]:
            assert check["status"] in ("PASS", "FAIL", "NOT_CHECKED")
            assert check["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    finally:
        db.close()


def test_e2e_api_error_paths():
    """Verify HTTP status codes and error responses for invalid inputs."""
    # 1. Nonexistent patient -> 404
    r1 = client.post(
        "/api/v1/substitutions/evaluate",
        json={"patient_id": 999999, "prescription_id": 1, "prescription_medication_id": 1, "original_medicine": "Med"},
    )
    assert r1.status_code == 404
    assert r1.json()["detail"] == "Patient record not found."

    # 2. Nonexistent prescription -> 404
    db = SessionLocal()
    try:
        pat = db.query(Patient).first()
        r2 = client.post(
            "/api/v1/substitutions/evaluate",
            json={"patient_id": pat.id, "prescription_id": 999999, "prescription_medication_id": 1, "original_medicine": "Med"},
        )
        assert r2.status_code == 404
        assert r2.json()["detail"] == "Prescription record not found."
    finally:
        db.close()

    # 3. Nonexistent prescription medication -> 404
    try:
        pat = db.query(Patient).first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        r3 = client.post(
            "/api/v1/substitutions/evaluate",
            json={"patient_id": pat.id, "prescription_id": rx.id, "prescription_medication_id": 999999, "original_medicine": "Med"},
        )
        assert r3.status_code == 404
        assert r3.json()["detail"] == "Prescription medication record not found."
    finally:
        db.close()

    # 4. Medication belonging to wrong prescription -> 400
    try:
        meds = db.query(PrescriptionMedication).all()
        med1, med2 = meds[0], meds[1]
        if med1.prescription_id != med2.prescription_id:
            rx = db.query(Prescription).filter_by(id=med1.prescription_id).first()
            r4 = client.post(
                "/api/v1/substitutions/evaluate",
                json={
                    "patient_id": rx.patient_id,
                    "prescription_id": rx.id,
                    "prescription_medication_id": med2.id,
                    "original_medicine": med2.medicine_name,
                },
            )
            assert r4.status_code == 400
            assert r4.json()["detail"] == "Prescription medication does not belong to the supplied prescription."
    finally:
        db.close()

    # 5. Prescription belonging to wrong patient -> 400
    try:
        pats = db.query(Patient).all()
        pat1, pat2 = pats[0], pats[1]
        rx2 = db.query(Prescription).filter_by(patient_id=pat2.id).first()
        med2 = db.query(PrescriptionMedication).filter_by(prescription_id=rx2.id).first()
        r5 = client.post(
            "/api/v1/substitutions/evaluate",
            json={
                "patient_id": pat1.id,
                "prescription_id": rx2.id,
                "prescription_medication_id": med2.id,
                "original_medicine": med2.medicine_name,
            },
        )
        assert r5.status_code == 400
        assert r5.json()["detail"] == "Prescription does not belong to the supplied patient."
    finally:
        db.close()

    # 6. Invalid payload schema -> 422
    r6 = client.post("/api/v1/substitutions/evaluate", json={"patient_id": "not_an_int"})
    assert r6.status_code == 422

    # 7. Sensitive data exposure check
    r7 = client.post(
        "/api/v1/substitutions/evaluate",
        json={"patient_id": 999999, "prescription_id": 1, "prescription_medication_id": 1, "original_medicine": "Med"},
    )
    body = r7.text.lower()
    assert "postgresql" not in body
    assert "password" not in body
    assert "traceback" not in body


def test_e2e_determinism():
    """Verify that repeated identical API requests yield identical DecisionResults."""
    db: Session = SessionLocal()
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

        res1 = client.post("/api/v1/substitutions/evaluate", json=payload).json()
        res2 = client.post("/api/v1/substitutions/evaluate", json=payload).json()

        assert res1 == res2
    finally:
        db.close()


def test_e2e_seed_data_idempotency():
    """Verify that re-running seed_synthetic_data is idempotent and inserts zero duplicate records."""
    counts = seed_synthetic_data()
    for entity, added_count in counts.items():
        assert added_count == 0, f"Expected 0 new records inserted for {entity}, got {added_count}"
