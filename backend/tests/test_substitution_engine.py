import json
import pytest
from pydantic import ValidationError
from app.schemas.substitution import (
    CheckResult,
    CheckStatus,
    DecisionResult,
    DecisionStatus,
    RiskLevel,
    SubstitutionRequest,
)
from app.services.substitution_engine import evaluate_substitution_foundation


def test_1_valid_decision_result_creation():
    """Verify that a valid DecisionResult object can be created."""
    res = DecisionResult(
        decision_status=DecisionStatus.RECOMMENDED,
        original_medicine="Amoxicillin 500mg Capsule",
        recommended_medicine="Cefalexin 500mg Capsule",
        reason="Alternative passed preliminary checks.",
        risk_level=RiskLevel.LOW,
        requires_human_confirmation=True,
        confidence_score=1.0,
        checks=[],
    )
    assert res.decision_status == DecisionStatus.RECOMMENDED
    assert res.original_medicine == "Amoxicillin 500mg Capsule"
    assert res.confidence_score == 1.0


def test_2_decision_status_supported_values():
    """Verify DecisionStatus accepts only supported Enum values."""
    assert set(e.value for e in DecisionStatus) == {
        "RECOMMENDED",
        "BLOCKED",
        "NO_ALTERNATIVE",
        "NEEDS_REVIEW",
    }
    with pytest.raises(ValueError):
        DecisionResult(
            decision_status="INVALID_STATUS",
            original_medicine="Med A",
            reason="Test",
            confidence_score=0.9,
        )


def test_3_check_result_pass():
    """Verify CheckResult can represent PASS status."""
    check = CheckResult(
        check_name="allergy_check",
        status=CheckStatus.PASS,
        reason="No patient allergy matches recorded for alternative.",
        evidence="Synthetic allergy log clear",
        severity=RiskLevel.LOW,
    )
    assert check.status == CheckStatus.PASS


def test_4_check_result_fail():
    """Verify CheckResult can represent FAIL status."""
    check = CheckResult(
        check_name="allergy_check",
        status=CheckStatus.FAIL,
        reason="Alternative conflicts with recorded patient allergy.",
        evidence="Patient has PENICILLIN allergy",
        severity=RiskLevel.CRITICAL,
    )
    assert check.status == CheckStatus.FAIL
    assert check.severity == RiskLevel.CRITICAL


def test_5_check_result_not_checked():
    """Verify CheckResult can represent NOT_CHECKED status."""
    check = CheckResult(
        check_name="prescriber_rule_check",
        status=CheckStatus.NOT_CHECKED,
        reason="Prescriber rule evaluation postponed to later step.",
        severity=RiskLevel.LOW,
    )
    assert check.status == CheckStatus.NOT_CHECKED


def test_6_final_result_contains_explainable_reason():
    """Verify final decision result contains human-readable explainable reason."""
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=1,
        prescription_medication_id=1,
        original_medicine="Amoxicillin 500mg Capsule",
    )
    fail_check = CheckResult(
        check_name="allergy_check",
        status=CheckStatus.FAIL,
        reason="Patient has severe Penicillin allergy.",
        evidence="Synthetic Allergy Record",
        severity=RiskLevel.HIGH,
    )
    res = evaluate_substitution_foundation(req, checks=[fail_check], proposed_alternative="Cefalexin 500mg Capsule")
    assert res.decision_status == DecisionStatus.BLOCKED
    assert "Substitution blocked due to clinical/patient constraints" in res.reason
    assert "Patient has severe Penicillin allergy" in res.reason


def test_7_confidence_score_range_validation():
    """Verify confidence_score enforces values between 0.0 and 1.0."""
    # Valid bounds
    res_low = DecisionResult(
        decision_status=DecisionStatus.RECOMMENDED,
        original_medicine="Med A",
        reason="Test",
        confidence_score=0.0,
    )
    res_high = DecisionResult(
        decision_status=DecisionStatus.RECOMMENDED,
        original_medicine="Med A",
        reason="Test",
        confidence_score=1.0,
    )
    assert res_low.confidence_score == 0.0
    assert res_high.confidence_score == 1.0

    # Invalid > 1.0
    with pytest.raises(ValidationError):
        DecisionResult(
            decision_status=DecisionStatus.RECOMMENDED,
            original_medicine="Med A",
            reason="Test",
            confidence_score=1.5,
        )

    # Invalid < 0.0
    with pytest.raises(ValidationError):
        DecisionResult(
            decision_status=DecisionStatus.RECOMMENDED,
            original_medicine="Med A",
            reason="Test",
            confidence_score=-0.1,
        )


def test_8_risk_level_supported_values():
    """Verify RiskLevel accepts all supported Enum values."""
    assert set(e.value for e in RiskLevel) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_9_engine_output_json_serializable():
    """Verify DecisionResult object is fully JSON serializable."""
    req = SubstitutionRequest(
        patient_id=1,
        prescription_id=10,
        prescription_medication_id=100,
        original_medicine="Amoxicillin 500mg Capsule",
    )
    check = CheckResult(
        check_name="stock_check",
        status=CheckStatus.PASS,
        reason="100 units available in inventory.",
        evidence="Stock Batch BATCH-0001",
        severity=RiskLevel.LOW,
    )
    res = evaluate_substitution_foundation(req, checks=[check], proposed_alternative="Cefalexin 500mg Capsule")

    # Serialize to JSON string
    json_str = res.model_dump_json()
    assert isinstance(json_str, str)

    # Deserialize back to dictionary
    data = json.loads(json_str)
    assert data["decision_status"] == "RECOMMENDED"
    assert data["checks"][0]["check_name"] == "stock_check"


def test_10_deterministic_output():
    """Verify that identical inputs produce identical DecisionResult outputs."""
    req = SubstitutionRequest(
        patient_id=2,
        prescription_id=5,
        prescription_medication_id=12,
        original_medicine="Ibuprofen 400mg Tablet",
    )
    check = CheckResult(
        check_name="allergy_check",
        status=CheckStatus.FAIL,
        reason="NSAID allergy matched",
        evidence="Allergy ID 4",
        severity=RiskLevel.HIGH,
    )

    res1 = evaluate_substitution_foundation(req, checks=[check], proposed_alternative="Naproxen 250mg Tablet")
    res2 = evaluate_substitution_foundation(req, checks=[check], proposed_alternative="Naproxen 250mg Tablet")

    assert res1.model_dump_json() == res2.model_dump_json()
