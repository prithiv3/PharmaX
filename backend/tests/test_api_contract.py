"""Step 3J - API Contract, Observability, Readiness, and Safety Regression Test Suite.

Comprehensive tests for all 11 system endpoints, request correlation tracing, duration logging,
sanitized log output, database readiness (GET /ready), and full safety regression validation against PostgreSQL.
"""

import logging
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

client = TestClient(app)
AUTH_HEADERS = {"X-Pharmacist-Token": "PHARM-TOKEN-101"}


def test_1_get_root_contract():
    """Verify GET / returns 200 OK with root message and X-Request-ID header."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Pharmacy Substitution Decision Support API"
    assert data["status"] == "running"
    assert "X-Request-ID" in res.headers


def test_2_get_health_contract():
    """Verify GET /health returns 200 OK with healthy status."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}
    assert "X-Request-ID" in res.headers


def test_3_get_ready_database_connected():
    """Verify GET /ready returns 200 OK when PostgreSQL connection SELECT 1 succeeds."""
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ready", "database": "connected"}
    assert "X-Request-ID" in res.headers


def test_4_get_ready_database_unavailable():
    """Verify GET /ready returns 503 SERVICE UNAVAILABLE when database is unreachable."""
    with patch("app.main.check_db_connection", return_value=False):
        res = client.get("/ready")
        assert res.status_code == 503
        assert res.json()["detail"] == "Database service unavailable."
        assert "postgresql://" not in res.text
        assert "password" not in res.text.lower()


def test_5_get_docs_openapi_contract():
    """Verify GET /docs returns 200 OK OpenAPI Swagger documentation."""
    res = client.get("/docs")
    assert res.status_code == 200
    assert "Pharmacy Substitution Decision Support API" in res.text


def test_6_post_evaluate_contract():
    """Verify POST /api/v1/substitutions/evaluate returns 200 OK with complete decision schema."""
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
        assert "decision_status" in data
        assert "original_medicine" in data
        assert "recommended_medicine" in data
        assert "checks" in data
        assert len(data["checks"]) == 9
        assert "X-Request-ID" in res.headers
    finally:
        db.close()


def test_7_get_substitutions_list_contract():
    """Verify GET /api/v1/substitutions returns 200 OK with total count and items array."""
    res = client.get("/api/v1/substitutions?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "X-Request-ID" in res.headers


def test_8_get_substitution_detail_contract():
    """Verify GET /api/v1/substitutions/{id} returns 200 OK with detail, checks, reviews, and audit logs."""
    db = SessionLocal()
    try:
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()
        decision_id = db_dec.id if db_dec else 1

        res = client.get(f"/api/v1/substitutions/{decision_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == decision_id
        assert "checks" in data
        assert "reviews" in data
        assert "audit_logs" in data
        assert "X-Request-ID" in res.headers
    finally:
        db.close()


def test_9_post_review_unauthenticated_and_authenticated_contracts():
    """Verify POST /api/v1/substitutions/{id}/review auth guard (401 without token, 200 with valid token)."""
    db = SessionLocal()
    try:
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()
        decision_id = db_dec.id

        # 1. Unauthenticated -> 401
        res_unauth = client.post(f"/api/v1/substitutions/{decision_id}/review", json={
            "pharmacist_code": "PHARM-CONTRACT-TEST",
            "review_status": "APPROVED",
        })
        assert res_unauth.status_code == 401
        assert "unauthorized" in res_unauth.json()["detail"].lower() or "missing" in res_unauth.json()["detail"].lower()

        # 2. Authenticated -> 200
        res_auth = client.post(
            f"/api/v1/substitutions/{decision_id}/review",
            json={
                "pharmacist_code": "PHARM-CONTRACT-TEST",
                "review_status": "APPROVED",
                "review_notes": "Contract test approval.",
            },
            headers=AUTH_HEADERS,
        )
        assert res_auth.status_code == 200
        assert res_auth.json()["reviews"][-1]["pharmacist_code"] == "PHARM-CONTRACT-TEST"
        assert "X-Request-ID" in res_auth.headers
    finally:
        db.close()


def test_10_get_analytics_summary_contract():
    """Verify GET /api/v1/substitutions/analytics/summary returns 200 OK with analytics metrics."""
    res = client.get("/api/v1/substitutions/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_decisions_evaluated" in data
    assert "status_distribution" in data
    assert "risk_level_distribution" in data
    assert "safety_block_breakdown" in data
    assert "X-Request-ID" in res.headers


def test_11_get_analytics_fairness_contract():
    """Verify GET /api/v1/substitutions/analytics/fairness returns 200 OK with fairness metrics."""
    res = client.get("/api/v1/substitutions/analytics/fairness")
    assert res.status_code == 200
    data = res.json()
    assert "age_group_metrics" in data
    assert "gender_metrics" in data
    assert "organ_impairment_metrics" in data
    assert "fairness_disparity_notes" in data
    assert "X-Request-ID" in res.headers


def test_12_get_analytics_error_analysis_contract():
    """Verify GET /api/v1/substitutions/analytics/error-analysis returns 200 OK with safety audit metrics."""
    res = client.get("/api/v1/substitutions/analytics/error-analysis")
    assert res.status_code == 200
    data = res.json()
    assert "root_cause_breakdown" in data
    assert "risk_level_breakdown" in data
    assert "X-Request-ID" in res.headers


def test_13_request_id_generation_and_propagation():
    """Verify middleware generates UUID when missing and preserves custom X-Request-ID."""
    # Test custom request ID
    custom_id = "test-correlation-uuid-999"
    res_custom = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res_custom.headers.get("X-Request-ID") == custom_id

    # Test auto-generated request ID
    res_gen = client.get("/health")
    assert "X-Request-ID" in res_gen.headers
    assert len(res_gen.headers["X-Request-ID"]) > 10


def test_14_request_duration_logging_and_sanitization(caplog):
    """Verify request duration logging captures method, path, status, and excludes sensitive tokens/passwords."""
    with caplog.at_level(logging.INFO):
        res = client.get("/health", headers=AUTH_HEADERS)
        assert res.status_code == 200
        log_text = caplog.text

        # Verify duration logging format
        assert "GET /health 200" in log_text
        assert "ms X-Request-ID=" in log_text

        # Verify log sanitization
        assert "PHARM-TOKEN-101" not in log_text
        assert "password" not in log_text.lower()
        assert "postgresql://" not in log_text


def test_15_safety_regression_all_10_scenarios():
    """Verify all 10 safety and evaluation regression scenarios on PostgreSQL."""
    db = SessionLocal()
    try:
        # Scenario 1: Safe evaluation (PAT-0001) -> RECOMMENDED or NEEDS_REVIEW
        pat1 = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx1 = db.query(Prescription).filter_by(patient_id=pat1.id).first()
        med1 = db.query(PrescriptionMedication).filter_by(prescription_id=rx1.id).first()
        res1 = client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat1.id, "prescription_id": rx1.id,
            "prescription_medication_id": med1.id, "original_medicine": med1.medicine_name,
        })
        assert res1.status_code == 200
        assert res1.json()["decision_status"] in ("RECOMMENDED", "NEEDS_REVIEW")

        # Scenario 2: Allergy conflict (PAT-0002) -> BLOCKED
        pat2 = db.query(Patient).filter_by(patient_code="PAT-0002").first()
        rx2 = db.query(Prescription).filter_by(patient_id=pat2.id).first()
        med2 = db.query(PrescriptionMedication).filter_by(prescription_id=rx2.id).first()
        res2 = client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat2.id, "prescription_id": rx2.id,
            "prescription_medication_id": med2.id, "original_medicine": med2.medicine_name,
        })
        assert res2.status_code == 200
        assert res2.json()["decision_status"] == "BLOCKED"

        # Scenario 3: Pregnancy contraindication (PAT-0003) -> BLOCKED
        pat3 = db.query(Patient).filter_by(patient_code="PAT-0003").first()
        rx3 = db.query(Prescription).filter_by(patient_id=pat3.id).first()
        med3 = db.query(PrescriptionMedication).filter_by(prescription_id=rx3.id).first()
        res3 = client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat3.id, "prescription_id": rx3.id,
            "prescription_medication_id": med3.id, "original_medicine": "Losartan 50mg Tablet",
            "requested_alternative": "Valsartan 80mg Tablet",
        })
        assert res3.status_code == 200
        assert res3.json()["decision_status"] == "BLOCKED"

        # Scenario 4: Age contraindication -> evaluate_age_check FAIL
        from app.models.clinical_constraint import ClinicalConstraint
        from app.services.substitution_engine import evaluate_age_check, CheckStatus
        c_age = ClinicalConstraint(medicine_name="Ciprofloxacin 500mg Tablet", constraint_type="AGE", constraint_rule="Contraindicated in pediatric under 18", severity="HIGH")
        age_res = evaluate_age_check(patient_exists=True, patient_age=12, candidate_medicine="Ciprofloxacin 500mg Tablet", constraints=[c_age])
        assert age_res.status == CheckStatus.FAIL

        # Scenario 5: Drug Interaction -> evaluate_drug_interaction_check FAIL
        from app.services.substitution_engine import evaluate_drug_interaction_check
        c_int = ClinicalConstraint(medicine_name="Clarithromycin 250mg Tablet", constraint_type="DRUG_INTERACTION", constraint_rule="Severe interaction with Atorvastatin", severity="CRITICAL")
        int_res = evaluate_drug_interaction_check(patient_exists=True, prescribed_medications=[PrescriptionMedication(medicine_name="Atorvastatin 20mg Tablet", active_ingredient="Atorvastatin")], candidate_medicine="Clarithromycin 250mg Tablet", constraints=[c_int])
        assert int_res.status == CheckStatus.FAIL

        # Scenario 6: Dosage Violation -> evaluate_dosage_check FAIL
        from app.services.substitution_engine import evaluate_dosage_check
        med_dose = PrescriptionMedication(medicine_name="Paracetamol 500mg Tablet", active_ingredient="Paracetamol", strength="500mg", dose="5000mg", frequency="QD")
        c_dose = ClinicalConstraint(medicine_name="Paracetamol 500mg Tablet", constraint_type="DOSAGE", constraint_rule="Maximum daily dose is 4000mg", severity="HIGH")
        dose_res = evaluate_dosage_check(patient_exists=True, prescribed_medication=med_dose, candidate_medicine="Paracetamol 500mg Tablet", constraints=[c_dose])
        assert dose_res.status == CheckStatus.FAIL

        # Scenario 7: Stock Unavailable (PAT-0005 with Gliclazide) -> BLOCKED
        pat7 = db.query(Patient).filter_by(patient_code="PAT-0005").first()
        rx7 = db.query(Prescription).filter_by(patient_id=pat7.id).first()
        med7 = db.query(PrescriptionMedication).filter_by(prescription_id=rx7.id).first()
        res7 = client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat7.id, "prescription_id": rx7.id,
            "prescription_medication_id": med7.id, "original_medicine": med7.medicine_name,
            "requested_alternative": "Gliclazide 80mg Tablet",
        })
        assert res7.status_code == 200
        assert res7.json()["decision_status"] in ("BLOCKED", "NO_ALTERNATIVE")

        # Scenario 8: All candidates unsafe -> recommended_medicine is null
        assert res2.json()["recommended_medicine"] is None

        # Scenario 9: Safe candidate selected deterministically
        assert res1.json()["recommended_medicine"] is not None

        # Scenario 10: Pharmacist review override with valid reason succeeds
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()
        res10 = client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={
                "pharmacist_code": "PHARM-SUP",
                "review_status": "OVERRIDDEN",
                "override_reason": "Clinical override verified during safety regression test.",
            },
            headers=AUTH_HEADERS,
        )
        assert res10.status_code == 200
        assert res10.json()["reviews"][-1]["override_reason"] == "Clinical override verified during safety regression test."
    finally:
        db.close()
