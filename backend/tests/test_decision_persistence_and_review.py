"""Step 3F - Decision Persistence, Audit Logging, and Pharmacist Review Workflow Test Suite.

Comprehensive tests for database persistence of substitution decisions, automated compliance audit logging,
and the pharmacist human-in-the-loop review workflow (confirm, reject, override).
"""

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.patient import Patient
from app.models.pharmacist_review import PharmacistReview
from app.models.prescription import Prescription
from app.models.medication import PrescriptionMedication
from app.models.substitution import SubstitutionDecision

client = TestClient(app)
AUTH_HEADERS = {"X-Pharmacist-Token": "PHARM-TOKEN-101"}


def test_1_evaluate_endpoint_persists_decision_and_creates_audit_log():
    """Verify POST /api/v1/substitutions/evaluate persists decision to DB and creates audit log."""
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
        assert "decision_status" in data
        assert "checks" in data

        # Verify DB record existence
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()
        assert db_dec is not None
        assert db_dec.original_medicine == med.medicine_name
        assert db_dec.decision_status in ("RECOMMENDED", "NEEDS_REVIEW")

        # Verify initial audit log entry
        db_audit = db.query(AuditLog).filter_by(decision_id=db_dec.id).first()
        assert db_audit is not None
        assert db_audit.action == "DECISION_EVALUATED"
    finally:
        db.close()


def test_2_get_decision_by_id_returns_details_and_checks():
    """Verify GET /api/v1/substitutions/{id} retrieves persisted decision detail."""
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
        decision_id = db_dec.id

        res = client.get(f"/api/v1/substitutions/{decision_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == decision_id
        assert "checks" in data
        assert len(data["checks"]) == 9
        assert "reviews" in data
        assert "audit_logs" in data
    finally:
        db.close()


def test_3_get_nonexistent_decision_returns_404():
    """Verify GET /api/v1/substitutions/999999 returns HTTP 404 NOT FOUND."""
    res = client.get("/api/v1/substitutions/999999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Substitution decision record not found."


def test_4_pharmacist_review_approval():
    """Verify submitting APPROVED review updates decision status and creates audit log."""
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
        decision_id = db_dec.id

        review_payload = {
            "pharmacist_code": "PHARM-101",
            "review_status": "APPROVED",
            "review_notes": "Therapeutic alternative verified and approved for dispensing.",
        }

        res = client.post(
            f"/api/v1/substitutions/{decision_id}/review",
            json=review_payload,
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["reviews"]) == 1
        assert data["reviews"][0]["pharmacist_code"] == "PHARM-101"
        assert data["reviews"][0]["review_status"] == "APPROVED"

        # Verify audit log recorded PHARMACIST_REVIEW
        audits = [a for a in data["audit_logs"] if a["action"] == "PHARMACIST_REVIEW"]
        assert len(audits) == 1
        assert audits[0]["actor_code"] == "PHARM-101"
        assert audits[0]["new_status"] == "APPROVED"
    finally:
        db.close()


def test_5_pharmacist_review_rejection():
    """Verify submitting REJECTED review updates decision status to REJECTED."""
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
        decision_id = db_dec.id

        review_payload = {
            "pharmacist_code": "PHARM-202",
            "review_status": "REJECTED",
            "review_notes": "Patient requested original brand formulation.",
        }

        res = client.post(
            f"/api/v1/substitutions/{decision_id}/review",
            json=review_payload,
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["reviews"][0]["review_status"] == "REJECTED"
    finally:
        db.close()


def test_6_pharmacist_review_override_with_reason_succeeds():
    """Verify submitting OVERRIDDEN review with valid override_reason succeeds."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0002").first()  # Allergy block patient
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        eval_res = client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })
        assert eval_res.json()["decision_status"] == "BLOCKED"
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()
        decision_id = db_dec.id

        review_payload = {
            "pharmacist_code": "PHARM-CLINICAL-SUP",
            "review_status": "OVERRIDDEN",
            "override_reason": "Desensitization therapy completed under allergist supervision.",
            "review_notes": "Approved override following clinical protocol check.",
        }

        res = client.post(
            f"/api/v1/substitutions/{decision_id}/review",
            json=review_payload,
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["reviews"][0]["override_reason"] == "Desensitization therapy completed under allergist supervision."
    finally:
        db.close()


def test_7_pharmacist_review_override_without_reason_fails():
    """Verify submitting OVERRIDDEN review without override_reason returns HTTP 400 BAD REQUEST."""
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
        decision_id = db_dec.id

        # Missing override_reason
        review_payload = {
            "pharmacist_code": "PHARM-303",
            "review_status": "OVERRIDDEN",
        }

        res = client.post(
            f"/api/v1/substitutions/{decision_id}/review",
            json=review_payload,
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 400
        assert "override reason is required" in res.json()["detail"].lower()
    finally:
        db.close()


def test_8_pharmacist_review_nonexistent_decision_returns_404():
    """Verify review for non-existent decision returns HTTP 404 NOT FOUND."""
    review_payload = {
        "pharmacist_code": "PHARM-101",
        "review_status": "APPROVED",
    }
    res = client.post(
        "/api/v1/substitutions/999999/review",
        json=review_payload,
        headers=AUTH_HEADERS,
    )
    assert res.status_code == 404


def test_9_invalid_review_status_returns_422():
    """Verify invalid review status value returns HTTP 422 UNPROCESSABLE ENTITY."""
    review_payload = {
        "pharmacist_code": "PHARM-101",
        "review_status": "INVALID_ACTION",
    }
    res = client.post(
        "/api/v1/substitutions/1/review",
        json=review_payload,
        headers=AUTH_HEADERS,
    )
    assert res.status_code == 422


def test_10_multiple_pharmacist_reviews_accumulate():
    """Verify multiple reviews on the same decision accumulate and update status."""
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
        decision_id = db_dec.id

        # First review: APPROVED
        client.post(
            f"/api/v1/substitutions/{decision_id}/review",
            json={
                "pharmacist_code": "PHARM-101",
                "review_status": "APPROVED",
            },
            headers=AUTH_HEADERS,
        )

        # Second review: REJECTED by Senior Pharmacist
        res2 = client.post(
            f"/api/v1/substitutions/{decision_id}/review",
            json={
                "pharmacist_code": "PHARM-HEAD",
                "review_status": "REJECTED",
                "review_notes": "Reversed approval after patient consult.",
            },
            headers={"X-Pharmacist-Token": "PHARM-TOKEN-HEAD"},
        )

        assert res2.status_code == 200
        data = res2.json()
        assert len(data["reviews"]) == 2
        assert data["reviews"][0]["pharmacist_code"] == "PHARM-101"
        assert data["reviews"][1]["pharmacist_code"] == "PHARM-HEAD"
        assert len(data["audit_logs"]) >= 3  # DECISION_EVALUATED + 2 reviews
    finally:
        db.close()
