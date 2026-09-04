"""Step 3G - Decision History Querying, Filtering, and Analytics Dashboard API Test Suite.

Comprehensive tests for decision listing/filtering endpoints, pagination controls,
real-time clinical decision support analytics summaries, safety block category metrics,
security, and determinism.
"""

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.medication import PrescriptionMedication
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.substitution import SubstitutionDecision

client = TestClient(app)


def test_1_list_substitutions_endpoint_returns_200():
    """Verify GET /api/v1/substitutions returns 200 OK with paginated list format."""
    res = client.get("/api/v1/substitutions")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_2_filter_substitutions_by_patient_id():
    """Verify filtering decision list by patient_id returns only matching patient decisions."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        # Generate a decision for PAT-0001
        client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })

        res = client.get(f"/api/v1/substitutions?patient_id={pat.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        for item in data["items"]:
            # Retrieve patient ID check
            db_dec = db.query(SubstitutionDecision).filter_by(id=item["id"]).first()
            assert db_dec.patient_id == pat.id
    finally:
        db.close()


def test_3_filter_substitutions_by_decision_status():
    """Verify filtering by decision_status (e.g., BLOCKED)."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0002").first()  # Allergy block patient
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })

        res = client.get("/api/v1/substitutions?decision_status=BLOCKED")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["decision_status"] == "BLOCKED"
    finally:
        db.close()


def test_4_filter_substitutions_by_risk_level():
    """Verify filtering decision list by risk_level (e.g., HIGH)."""
    res = client.get("/api/v1/substitutions?risk_level=HIGH")
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert item["risk_level"] == "HIGH"


def test_5_pagination_limit_and_offset_controls():
    """Verify limit and offset pagination parameters."""
    res_page1 = client.get("/api/v1/substitutions?limit=2&offset=0")
    assert res_page1.status_code == 200
    data1 = res_page1.json()
    assert data1["limit"] == 2
    assert data1["offset"] == 0
    assert len(data1["items"]) <= 2

    res_page2 = client.get("/api/v1/substitutions?limit=2&offset=2")
    assert res_page2.status_code == 200
    data2 = res_page2.json()
    assert data2["limit"] == 2
    assert data2["offset"] == 2


def test_6_invalid_pagination_parameters_returns_422():
    """Verify limit > 100 or limit < 1 returns 422 UNPROCESSABLE ENTITY."""
    res_large = client.get("/api/v1/substitutions?limit=500")
    assert res_large.status_code == 422

    res_zero = client.get("/api/v1/substitutions?limit=0")
    assert res_zero.status_code == 422


def test_7_analytics_summary_endpoint_returns_200():
    """Verify GET /api/v1/substitutions/analytics/summary returns 200 OK with valid metrics structure."""
    res = client.get("/api/v1/substitutions/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_decisions_evaluated" in data
    assert "status_distribution" in data
    assert "risk_level_distribution" in data
    assert "safety_block_breakdown" in data
    assert "total_pharmacist_reviews" in data
    assert "total_pharmacist_overrides" in data


def test_8_analytics_summary_safety_block_breakdown_fields():
    """Verify safety block breakdown includes all 8 safety check categories."""
    res = client.get("/api/v1/substitutions/analytics/summary")
    assert res.status_code == 200
    breakdown = res.json()["safety_block_breakdown"]
    required_keys = [
        "allergy_blocks",
        "renal_blocks",
        "hepatic_blocks",
        "pregnancy_blocks",
        "age_blocks",
        "drug_interaction_blocks",
        "dosage_blocks",
        "stock_blocks",
    ]
    for key in required_keys:
        assert key in breakdown
        assert isinstance(breakdown[key], int)


def test_9_analytics_summary_reflects_evaluated_decisions():
    """Verify analytics summary counts increase after evaluating new decisions."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        res_before = client.get("/api/v1/substitutions/analytics/summary").json()
        count_before = res_before["total_decisions_evaluated"]

        client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })

        res_after = client.get("/api/v1/substitutions/analytics/summary").json()
        count_after = res_after["total_decisions_evaluated"]

        assert count_after == count_before + 1
    finally:
        db.close()


def test_10_analytics_summary_reflects_pharmacist_overrides():
    """Verify analytics summary tracks total pharmacist overrides accurately."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0002").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        res_eval = client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()

        res_before = client.get("/api/v1/substitutions/analytics/summary").json()
        overrides_before = res_before["total_pharmacist_overrides"]

        client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={
                "pharmacist_code": "PHARM-ANALYTICS-TEST",
                "review_status": "OVERRIDDEN",
                "override_reason": "Clinical override for analytics test.",
            },
            headers={"X-Pharmacist-Token": "PHARM-TOKEN-101"},
        )

        res_after = client.get("/api/v1/substitutions/analytics/summary").json()
        overrides_after = res_after["total_pharmacist_overrides"]

        assert overrides_after == overrides_before + 1
    finally:
        db.close()


def test_11_repeated_analytics_summary_calls_return_identical_json():
    """Verify deterministic repeatability for consecutive analytics requests."""
    res1 = client.get("/api/v1/substitutions/analytics/summary")
    res2 = client.get("/api/v1/substitutions/analytics/summary")

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.text == res2.text


def test_12_no_sensitive_information_leaked_in_analytics():
    """Verify analytics output does not leak passwords or internal tracebacks."""
    res = client.get("/api/v1/substitutions/analytics/summary")
    json_str = res.text.lower()

    assert "password" not in json_str
    assert "secret" not in json_str
    assert "traceback" not in json_str
    assert "sqlalchemy" not in json_str


def test_13_sql_injection_resilience_in_filters():
    """Verify malicious SQL injection string in query filter is safely handled."""
    malicious_status = "BLOCKED' OR 1=1 --"
    res = client.get(f"/api/v1/substitutions?decision_status={malicious_status}")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0  # Safely parameterized by SQLAlchemy ORM


def test_14_end_to_end_evaluate_review_analytics_pipeline():
    """End-to-end integration test verifying evaluate -> review -> list -> analytics summary pipeline."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        # Step A: Evaluate
        res_eval = client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })
        assert res_eval.status_code == 200
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()

        # Step B: Review
        res_rev = client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={
                "pharmacist_code": "PHARM-E2E",
                "review_status": "APPROVED",
            },
            headers={"X-Pharmacist-Token": "PHARM-TOKEN-101"},
        )
        assert res_rev.status_code == 200

        # Step C: List & verify item presence
        res_list = client.get(f"/api/v1/substitutions?patient_id={pat.id}")
        assert res_list.status_code == 200
        found_ids = [item["id"] for item in res_list.json()["items"]]
        assert db_dec.id in found_ids

        # Step D: Analytics summary verification
        res_summary = client.get("/api/v1/substitutions/analytics/summary")
        assert res_summary.status_code == 200
        assert res_summary.json()["total_decisions_evaluated"] >= 1
    finally:
        db.close()


def test_15_empty_query_result_returns_clean_response():
    """Verify non-matching filter returns HTTP 200 OK with total=0 and empty items list."""
    res = client.get("/api/v1/substitutions?patient_id=999999")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["items"] == []
