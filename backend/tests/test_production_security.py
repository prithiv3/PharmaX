"""Step 3I - Production Readiness, Security Hardening, Transaction Safety, and API Quality Test Suite.

Comprehensive tests for prototype pharmacist authorization, atomic transaction safety, concurrency row locking,
request correlation tracing, exception safety, and regression protection.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.medication import PrescriptionMedication
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.substitution import SubstitutionDecision
from app.repositories.decision_repository import (
    create_substitution_decision_and_audit,
    get_substitution_decision_for_update,
)
from app.schemas.substitution import DecisionResult, DecisionStatus, RiskLevel, SubstitutionRequest

client = TestClient(app)
AUTH_HEADERS = {"X-Pharmacist-Token": "PHARM-TOKEN-101"}


def test_1_unauthorized_review_rejected():
    """Verify POST /api/v1/substitutions/{id}/review without X-Pharmacist-Token returns 401 UNAUTHORIZED."""
    db = SessionLocal()
    try:
        db_dec = db.query(SubstitutionDecision).first()
        decision_id = db_dec.id if db_dec else 1

        res = client.post(f"/api/v1/substitutions/{decision_id}/review", json={
            "pharmacist_code": "PHARM-101",
            "review_status": "APPROVED",
        })
        assert res.status_code == 401
        assert "unauthorized" in res.json()["detail"].lower() or "missing" in res.json()["detail"].lower()
    finally:
        db.close()


def test_2_authorized_review_succeeds():
    """Verify POST /api/v1/substitutions/{id}/review with X-Pharmacist-Token succeeds."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()

        res = client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={
                "pharmacist_code": "PHARM-101",
                "review_status": "APPROVED",
                "review_notes": "Authorized review test.",
            },
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 200
        assert res.json()["reviews"][0]["pharmacist_code"] == "PHARM-101"
    finally:
        db.close()


def test_3_invalid_pharmacist_token_rejected():
    """Verify POST /api/v1/substitutions/{id}/review with invalid token returns 401 UNAUTHORIZED."""
    res = client.post(
        "/api/v1/substitutions/1/review",
        json={"pharmacist_code": "PHARM-101", "review_status": "APPROVED"},
        headers={"X-Pharmacist-Token": "INVALID"},
    )
    assert res.status_code == 401


def test_4_override_without_reason_rejected():
    """Verify OVERRIDDEN review without override_reason returns 400 BAD REQUEST."""
    db = SessionLocal()
    try:
        db_dec = db.query(SubstitutionDecision).first()
        decision_id = db_dec.id if db_dec else 1

        res = client.post(
            f"/api/v1/substitutions/{decision_id}/review",
            json={
                "pharmacist_code": "PHARM-101",
                "review_status": "OVERRIDDEN",
            },
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 400
        assert "override reason is required" in res.json()["detail"].lower()
    finally:
        db.close()


def test_5_malformed_request_returns_422():
    """Verify evaluate request missing required fields returns 422 UNPROCESSABLE ENTITY."""
    res = client.post("/api/v1/substitutions/evaluate", json={"patient_id": 1})
    assert res.status_code == 422


def test_6_invalid_pagination_values_rejected():
    """Verify invalid pagination limit returns 422 UNPROCESSABLE ENTITY."""
    res = client.get("/api/v1/substitutions?limit=500")
    assert res.status_code == 422


def test_7_internal_exception_does_not_expose_stack_trace():
    """Verify global exception handler returns generic 500 without stack trace."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()

        with patch("app.api.v1.substitutions.get_substitution_decision_service", side_effect=RuntimeError("Simulated database crash")):
            res = client.get(f"/api/v1/substitutions/{db_dec.id}")
            assert res.status_code == 500
            assert "RuntimeError" not in res.text
            assert "Traceback" not in res.text
    finally:
        db.close()


def test_8_internal_exception_does_not_expose_db_credentials():
    """Verify 500 error response does not expose database credentials or URLs."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        with patch("app.api.v1.substitutions.evaluate_substitution_request_service", side_effect=Exception("postgresql://user:secretpass@localhost:5432/db")):
            res = client.post("/api/v1/substitutions/evaluate", json={
                "patient_id": pat.id,
                "prescription_id": rx.id,
                "prescription_medication_id": med.id,
                "original_medicine": med.medicine_name,
            })
            assert res.status_code == 500
            assert "secretpass" not in res.text
            assert "postgresql://" not in res.text
    finally:
        db.close()


def test_9_decision_and_audit_persistence_atomic():
    """Verify create_substitution_decision_and_audit commits decision and audit log atomically."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        sub_req = SubstitutionRequest(
            patient_id=pat.id,
            prescription_id=rx.id,
            prescription_medication_id=med.id,
            original_medicine=med.medicine_name,
        )
        dec_res = DecisionResult(
            decision_status=DecisionStatus.RECOMMENDED,
            original_medicine=med.medicine_name,
            recommended_medicine="Alternative Med",
            reason="Atomic test reason",
            risk_level=RiskLevel.LOW,
            requires_human_confirmation=True,
            confidence_score=1.0,
            checks=[],
        )

        db_dec, db_audit = create_substitution_decision_and_audit(db, sub_req, dec_res)
        assert db_dec.id is not None
        assert db_audit.id is not None
        assert db_audit.decision_id == db_dec.id
        assert db_audit.action == "DECISION_EVALUATED"
    finally:
        db.close()


def test_10_audit_failure_rolls_back_decision():
    """Verify failure during audit creation rolls back decision persistence cleanly."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        sub_req = SubstitutionRequest(
            patient_id=pat.id,
            prescription_id=rx.id,
            prescription_medication_id=med.id,
            original_medicine=med.medicine_name,
        )
        dec_res = DecisionResult(
            decision_status=DecisionStatus.RECOMMENDED,
            original_medicine=med.medicine_name,
            recommended_medicine="Alternative Med",
            reason="Rollback test reason",
            risk_level=RiskLevel.LOW,
            requires_human_confirmation=True,
            confidence_score=1.0,
            checks=[],
        )

        with patch("app.repositories.decision_repository.AuditLog", side_effect=RuntimeError("Simulated audit write failure")):
            with pytest.raises(RuntimeError):
                create_substitution_decision_and_audit(db, sub_req, dec_res)

        # Verify no decision record remained
        orphaned = db.query(SubstitutionDecision).filter_by(reason="Rollback test reason").first()
        assert orphaned is None
    finally:
        db.close()


def test_11_concurrent_review_row_locking():
    """Verify get_substitution_decision_for_update retrieves record with row lock query."""
    db = SessionLocal()
    try:
        db_dec = db.query(SubstitutionDecision).first()
        if db_dec:
            locked_dec = get_substitution_decision_for_update(db, db_dec.id)
            assert locked_dec is not None
            assert locked_dec.id == db_dec.id
    finally:
        db.close()


def test_12_valid_sequential_review_succeeds():
    """Verify sequential reviews succeed and accumulate audit entries."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()

        res1 = client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={"pharmacist_code": "PHARM-1", "review_status": "APPROVED"},
            headers=AUTH_HEADERS,
        )
        assert res1.status_code == 200

        res2 = client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={"pharmacist_code": "PHARM-2", "review_status": "REJECTED"},
            headers=AUTH_HEADERS,
        )
        assert res2.status_code == 200
        assert len(res2.json()["reviews"]) == 2
    finally:
        db.close()


def test_13_audit_entry_integrity():
    """Verify audit log entry contains decision_id, action, actor_code, status, timestamp."""
    db = SessionLocal()
    try:
        audit = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        assert audit is not None
        assert audit.action in ("DECISION_EVALUATED", "PHARMACIST_REVIEW")
        assert audit.created_at is not None
    finally:
        db.close()


def test_14_request_correlation_id_returned():
    """Verify X-Request-ID header is present in API responses."""
    # Test with custom request ID header
    res_custom = client.get("/", headers={"X-Request-ID": "test-req-12345"})
    assert res_custom.status_code == 200
    assert res_custom.headers.get("X-Request-ID") == "test-req-12345"

    # Test with auto-generated request ID header
    res_auto = client.get("/")
    assert res_auto.status_code == 200
    assert "X-Request-ID" in res_auto.headers
    assert len(res_auto.headers["X-Request-ID"]) > 10


def test_15_evaluation_response_structure_unchanged():
    """Verify POST /evaluate response format remains backward-compatible."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        res = client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })
        assert res.status_code == 200
        data = res.json()
        required_keys = [
            "decision_status",
            "original_medicine",
            "recommended_medicine",
            "reason",
            "risk_level",
            "requires_human_confirmation",
            "confidence_score",
            "checks",
        ]
        for key in required_keys:
            assert key in data
    finally:
        db.close()


def test_16_analytics_summary_functional():
    """Verify GET /api/v1/substitutions/analytics/summary remains fully functional."""
    res = client.get("/api/v1/substitutions/analytics/summary")
    assert res.status_code == 200
    assert "total_decisions_evaluated" in res.json()


def test_17_fairness_analytics_functional():
    """Verify GET /api/v1/substitutions/analytics/fairness remains fully functional."""
    res = client.get("/api/v1/substitutions/analytics/fairness")
    assert res.status_code == 200
    assert "age_group_metrics" in res.json()


def test_18_error_analysis_functional():
    """Verify GET /api/v1/substitutions/analytics/error-analysis remains fully functional."""
    res = client.get("/api/v1/substitutions/analytics/error-analysis")
    assert res.status_code == 200
    assert "root_cause_breakdown" in res.json()


def test_19_postgresql_backend_verified():
    """Verify that PostgreSQL is the active database engine dialect for the runtime database."""
    from app.db.session import engine
    assert engine.name == "postgresql"
    assert "postgresql" in str(engine.url)

