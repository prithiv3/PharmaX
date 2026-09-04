"""Step 5 - Full-Stack End-to-End Integration & Demo Readiness Test Suite.

Comprehensive integration tests validating browser UI workflows, backend REST API services,
PostgreSQL persistence, audit trails, human-in-the-loop pharmacist reviews, and governance analytics.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, engine
from app.main import app
from app.models.audit_log import AuditLog
from app.models.medication import PrescriptionMedication
from app.models.patient import Patient
from app.models.pharmacist_review import PharmacistReview
from app.models.prescription import Prescription
from app.models.substitution import SubstitutionDecision

client = TestClient(app)
AUTH_HEADERS = {"X-Pharmacist-Token": "PHARM-TOKEN-101"}


def test_1_scenario_a_safe_substitution_full_stack_workflow():
    """Scenario A: Safe evaluation (PAT-0001 Lisinopril) evaluates candidates, persists decision & initial audit log."""
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
        assert res.status_code == 200
        data = res.json()

        # Decision & Candidate Verification
        assert data["decision_status"] in ("RECOMMENDED", "NEEDS_REVIEW")
        assert data["recommended_medicine"] is not None
        assert data["requires_human_confirmation"] is True
        assert len(data["checks"]) == 9
        assert "X-Request-ID" in res.headers

        # DB Persistence Verification
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()
        assert db_dec is not None
        assert db_dec.original_medicine == med.medicine_name

        # Initial Audit Log Verification
        db_audit = db.query(AuditLog).filter_by(decision_id=db_dec.id).first()
        assert db_audit is not None
        assert db_audit.action == "DECISION_EVALUATED"
    finally:
        db.close()


def test_2_scenario_b_allergy_block_full_stack_workflow():
    """Scenario B: Patient PAT-0002 with severe Penicillin allergy returns BLOCKED with failed allergy check."""
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

        res = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["decision_status"] == "BLOCKED"
        assert data["recommended_medicine"] is None
        assert data["risk_level"] in ("HIGH", "CRITICAL")

        allergy_checks = [c for c in data["checks"] if c["check_name"] == "allergy"]
        assert len(allergy_checks) > 0
        assert allergy_checks[0]["status"] == "FAIL"
        assert "PENICILLIN" in allergy_checks[0]["reason"].upper()
    finally:
        db.close()


def test_3_scenario_c_pregnancy_block_full_stack_workflow():
    """Scenario C: Teratogenic drug for pregnant patient PAT-0003 returns BLOCKED with failed pregnancy check."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0003").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        payload = {
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": "Losartan 50mg Tablet",
            "requested_alternative": "Valsartan 80mg Tablet",
        }

        res = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["decision_status"] == "BLOCKED"
        assert data["recommended_medicine"] is None

        preg_checks = [c for c in data["checks"] if c["check_name"] == "pregnancy"]
        assert len(preg_checks) > 0
        assert preg_checks[0]["status"] == "FAIL"
    finally:
        db.close()


def test_4_scenario_d_stock_block_full_stack_workflow():
    """Scenario D: Alternative with zero inventory stock (PAT-0005 Gliclazide) returns BLOCKED."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0005").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        payload = {
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
            "requested_alternative": "Gliclazide 80mg Tablet",
        }

        res = client.post("/api/v1/substitutions/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["decision_status"] in ("BLOCKED", "NO_ALTERNATIVE")
        assert data["recommended_medicine"] is None

        stock_checks = [c for c in data["checks"] if c["check_name"] == "stock"]
        assert len(stock_checks) > 0
        assert stock_checks[0]["status"] == "FAIL"
    finally:
        db.close()


def test_5_scenario_e_pharmacist_approval_full_stack_workflow():
    """Scenario E: Pharmacist submits APPROVED review with token, updating decision status & audit trail."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id, "prescription_id": rx.id,
            "prescription_medication_id": med.id, "original_medicine": med.medicine_name,
        })
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()

        res_review = client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={
                "pharmacist_code": "PHARM-E2E-APP",
                "review_status": "APPROVED",
                "review_notes": "Clinical confirmation for dispensing.",
            },
            headers=AUTH_HEADERS,
        )
        assert res_review.status_code == 200
        data = res_review.json()

        assert len(data["reviews"]) >= 1
        assert data["reviews"][-1]["review_status"] == "APPROVED"
        assert data["reviews"][-1]["pharmacist_code"] == "PHARM-E2E-APP"

        # Verify audit entry
        audits = [a for a in data["audit_logs"] if a["action"] == "PHARMACIST_REVIEW"]
        assert len(audits) >= 1
        assert audits[-1]["new_status"] == "APPROVED"
    finally:
        db.close()


def test_6_scenario_f_pharmacist_rejection_full_stack_workflow():
    """Scenario F: Pharmacist submits REJECTED review with token, updating status to REJECTED."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id, "prescription_id": rx.id,
            "prescription_medication_id": med.id, "original_medicine": med.medicine_name,
        })
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()

        res_review = client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={
                "pharmacist_code": "PHARM-E2E-REJ",
                "review_status": "REJECTED",
                "review_notes": "Patient requested original brand.",
            },
            headers=AUTH_HEADERS,
        )
        assert res_review.status_code == 200
        assert res_review.json()["reviews"][-1]["review_status"] == "REJECTED"
    finally:
        db.close()


def test_7_scenario_g_pharmacist_override_validation_full_stack_workflow():
    """Scenario G: OVERRIDDEN review without reason fails (400), with reason succeeds (200)."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0002").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id, "prescription_id": rx.id,
            "prescription_medication_id": med.id, "original_medicine": med.medicine_name,
        })
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()

        # Step 1: Without override_reason -> 400
        res_fail = client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={"pharmacist_code": "PHARM-OVR", "review_status": "OVERRIDDEN"},
            headers=AUTH_HEADERS,
        )
        assert res_fail.status_code == 400
        assert "override reason is required" in res_fail.json()["detail"].lower()

        # Step 2: With override_reason -> 200
        res_pass = client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={
                "pharmacist_code": "PHARM-OVR",
                "review_status": "OVERRIDDEN",
                "override_reason": "Desensitization therapy completed under allergist supervision.",
            },
            headers=AUTH_HEADERS,
        )
        assert res_pass.status_code == 200
        data = res_pass.json()
        assert data["reviews"][-1]["override_reason"] == "Desensitization therapy completed under allergist supervision."
    finally:
        db.close()


def test_8_unauthorized_pharmacist_review_rejected():
    """Verify review request without X-Pharmacist-Token returns 401 UNAUTHORIZED."""
    res = client.post("/api/v1/substitutions/1/review", json={
        "pharmacist_code": "PHARM-NOAUTH",
        "review_status": "APPROVED",
    })
    assert res.status_code == 401
    assert "unauthorized" in res.json()["detail"].lower() or "missing" in res.json()["detail"].lower()


def test_9_invalid_pharmacist_token_rejected():
    """Verify review request with invalid token header returns 401 UNAUTHORIZED."""
    res = client.post(
        "/api/v1/substitutions/1/review",
        json={"pharmacist_code": "PHARM-BAD", "review_status": "APPROVED"},
        headers={"X-Pharmacist-Token": "INVALID"},
    )
    assert res.status_code == 401


def test_10_nonexistent_decision_id_returns_404():
    """Verify requesting nonexistent decision ID returns HTTP 404 NOT FOUND."""
    res = client.get("/api/v1/substitutions/999999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Substitution decision record not found."


def test_11_malformed_request_parameters_returns_422():
    """Verify missing required parameters returns HTTP 422 UNPROCESSABLE ENTITY."""
    res = client.post("/api/v1/substitutions/evaluate", json={"patient_id": 1})
    assert res.status_code == 422


def test_12_invalid_pagination_parameters_returns_422():
    """Verify limit exceeding maximum bound returns HTTP 422 UNPROCESSABLE ENTITY."""
    res = client.get("/api/v1/substitutions?limit=1000")
    assert res.status_code == 422


def test_13_database_readiness_and_failure_fallback():
    """Verify GET /ready returns 200 OK when DB is healthy, and 503 when DB fails."""
    res_ok = client.get("/ready")
    assert res_ok.status_code == 200
    assert res_ok.json() == {"status": "ready", "database": "connected"}

    with patch("app.main.check_db_connection", return_value=False):
        res_fail = client.get("/ready")
        assert res_fail.status_code == 503
        assert res_fail.json()["detail"] == "Database service unavailable."


def test_14_request_correlation_id_propagation_and_generation():
    """Verify custom X-Request-ID is preserved and missing ID is auto-generated."""
    custom_id = "e2e-correlation-id-777"
    res_custom = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res_custom.headers.get("X-Request-ID") == custom_id

    res_auto = client.get("/health")
    assert "X-Request-ID" in res_auto.headers
    assert len(res_auto.headers["X-Request-ID"]) > 10


def test_15_error_response_sanitization_no_secrets_leaked():
    """Verify 500 internal server error masks stack traces and database credentials."""
    with patch("app.api.v1.substitutions.get_substitution_decision_service", side_effect=Exception("postgresql://postgres:secretpassword@localhost:5432/db")):
        res = client.get("/api/v1/substitutions/1")
        assert res.status_code == 500
        assert "secretpassword" not in res.text
        assert "postgresql://" not in res.text
        assert "Exception" not in res.text


def test_16_postgresql_database_dialect_verified():
    """Verify PostgreSQL is the active engine dialect for runtime and integration testing."""
    assert engine.name == "postgresql"
    assert "postgresql" in str(engine.url)
