"""Step 3H - Synthetic Population Bias & Fairness Evaluation and Error Analysis Framework Test Suite.

Comprehensive tests for demographic cohort fairness evaluation, clinical safety audit reporting,
safety block root cause breakdowns, security, and determinism.
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


def test_1_get_population_fairness_returns_200():
    """Verify GET /api/v1/substitutions/analytics/fairness returns 200 OK with valid metrics structure."""
    res = client.get("/api/v1/substitutions/analytics/fairness")
    assert res.status_code == 200
    data = res.json()
    assert "age_group_metrics" in data
    assert "gender_metrics" in data
    assert "organ_impairment_metrics" in data
    assert "fairness_disparity_notes" in data
    assert isinstance(data["age_group_metrics"], list)


def test_2_population_fairness_age_group_cohorts():
    """Verify age group cohorts include pediatrics, adults, and geriatrics."""
    res = client.get("/api/v1/substitutions/analytics/fairness")
    assert res.status_code == 200
    age_cohorts = res.json()["age_group_metrics"]
    segment_names = [item["segment_name"] for item in age_cohorts]
    assert "Pediatrics (<18)" in segment_names
    assert "Adults (18-64)" in segment_names
    assert "Geriatrics (>=65)" in segment_names


def test_3_population_fairness_organ_impairment_cohorts():
    """Verify organ impairment cohorts include renal, hepatic, and normal organ function."""
    res = client.get("/api/v1/substitutions/analytics/fairness")
    assert res.status_code == 200
    organ_cohorts = res.json()["organ_impairment_metrics"]
    segment_names = [item["segment_name"] for item in organ_cohorts]
    assert "Renal Impairment" in segment_names
    assert "Hepatic Impairment" in segment_names
    assert "Normal Organ Function" in segment_names


def test_4_get_error_analysis_returns_200():
    """Verify GET /api/v1/substitutions/analytics/error-analysis returns 200 OK."""
    res = client.get("/api/v1/substitutions/analytics/error-analysis")
    assert res.status_code == 200
    data = res.json()
    assert "total_decisions_analyzed" in data
    assert "total_blocks" in data
    assert "block_rate" in data
    assert "average_confidence_score" in data
    assert "risk_level_breakdown" in data
    assert "root_cause_breakdown" in data
    assert "average_checks_evaluated_per_request" in data


def test_5_error_analysis_root_cause_categories():
    """Verify root cause breakdown contains all 8 safety check categories."""
    res = client.get("/api/v1/substitutions/analytics/error-analysis")
    assert res.status_code == 200
    causes = res.json()["root_cause_breakdown"]
    expected_categories = [
        "Allergy Contraindication",
        "Renal Impairment Contraindication",
        "Hepatic Impairment Contraindication",
        "Pregnancy Contraindication",
        "Age Limit Contraindication",
        "Drug-Drug Interaction",
        "Dosage Limit Exceeded",
        "Stock Depletion / Unavailable",
    ]
    for category in expected_categories:
        assert category in causes
        assert isinstance(causes[category], int)


def test_6_fairness_metrics_update_after_new_evaluation():
    """Verify demographic fairness metrics update dynamically after evaluating new decisions."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        res_before = client.get("/api/v1/substitutions/analytics/fairness").json()

        client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })

        res_after = client.get("/api/v1/substitutions/analytics/fairness").json()
        assert res_after != res_before
    finally:
        db.close()


def test_7_error_analysis_block_rate_calculation():
    """Verify block rate calculation in error analysis is bounded between 0.0 and 1.0."""
    res = client.get("/api/v1/substitutions/analytics/error-analysis")
    assert res.status_code == 200
    data = res.json()
    assert 0.0 <= data["block_rate"] <= 1.0
    assert 0.0 <= data["average_confidence_score"] <= 1.0


def test_8_repeated_fairness_calls_return_identical_json():
    """Verify deterministic repeatability for consecutive demographic fairness calls."""
    res1 = client.get("/api/v1/substitutions/analytics/fairness")
    res2 = client.get("/api/v1/substitutions/analytics/fairness")
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.text == res2.text


def test_9_repeated_error_analysis_calls_return_identical_json():
    """Verify deterministic repeatability for consecutive error analysis calls."""
    res1 = client.get("/api/v1/substitutions/analytics/error-analysis")
    res2 = client.get("/api/v1/substitutions/analytics/error-analysis")
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.text == res2.text


def test_10_no_patient_pii_in_fairness_analytics():
    """Verify fairness analytics output contains zero individual patient PII."""
    res = client.get("/api/v1/substitutions/analytics/fairness")
    json_str = res.text.lower()
    assert "patient_id" not in json_str
    assert "patient_code" not in json_str
    assert "first_name" not in json_str
    assert "last_name" not in json_str


def test_11_no_sensitive_secrets_or_stack_traces_leaked():
    """Verify error analysis output does not leak passwords or internal tracebacks."""
    res = client.get("/api/v1/substitutions/analytics/error-analysis")
    json_str = res.text.lower()
    assert "password" not in json_str
    assert "secret" not in json_str
    assert "traceback" not in json_str
    assert "sqlalchemy" not in json_str


def test_12_nonexistent_analytics_subpath_returns_404():
    """Verify invalid analytics subpath returns 404 NOT FOUND."""
    res = client.get("/api/v1/substitutions/analytics/nonexistent")
    assert res.status_code == 404


def test_13_complete_substitutions_analytics_pipeline():
    """End-to-end integration test verifying complete evaluate -> review -> list -> analytics -> fairness -> error analysis pipeline."""
    db = SessionLocal()
    try:
        pat = db.query(Patient).filter_by(patient_code="PAT-0001").first()
        rx = db.query(Prescription).filter_by(patient_id=pat.id).first()
        med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()

        # 1. Evaluate
        res_eval = client.post("/api/v1/substitutions/evaluate", json={
            "patient_id": pat.id,
            "prescription_id": rx.id,
            "prescription_medication_id": med.id,
            "original_medicine": med.medicine_name,
        })
        assert res_eval.status_code == 200
        db_dec = db.query(SubstitutionDecision).order_by(SubstitutionDecision.id.desc()).first()

        # 2. Review
        res_rev = client.post(
            f"/api/v1/substitutions/{db_dec.id}/review",
            json={
                "pharmacist_code": "PHARM-STEP3H",
                "review_status": "APPROVED",
            },
            headers={"X-Pharmacist-Token": "PHARM-TOKEN-101"},
        )
        assert res_rev.status_code == 200

        # 3. List
        res_list = client.get(f"/api/v1/substitutions?patient_id={pat.id}")
        assert res_list.status_code == 200

        # 4. Summary Analytics
        res_summary = client.get("/api/v1/substitutions/analytics/summary")
        assert res_summary.status_code == 200

        # 5. Demographic Fairness Analytics
        res_fairness = client.get("/api/v1/substitutions/analytics/fairness")
        assert res_fairness.status_code == 200

        # 6. Error Analysis
        res_err = client.get("/api/v1/substitutions/analytics/error-analysis")
        assert res_err.status_code == 200
    finally:
        db.close()


def test_14_fairness_disparity_notes_present():
    """Verify fairness response includes explanatory disparity notes for clinical transparency."""
    res = client.get("/api/v1/substitutions/analytics/fairness")
    assert res.status_code == 200
    notes = res.json()["fairness_disparity_notes"]
    assert len(notes) >= 1
    assert any("safety" in note.lower() for note in notes)


def test_15_error_analysis_average_checks_evaluated():
    """Verify error analysis reports average checks evaluated as 9.0."""
    res = client.get("/api/v1/substitutions/analytics/error-analysis")
    assert res.status_code == 200
    assert res.json()["average_checks_evaluated_per_request"] == 9.0
