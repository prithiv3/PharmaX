"""Alternative Ranking Service - Pure deterministic candidate evaluation and best alternative selection."""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple

from app.models.allergy import Allergy
from app.models.alternative import MedicineAlternative
from app.models.clinical_constraint import ClinicalConstraint
from app.models.medication import PrescriptionMedication
from app.models.patient import Patient
from app.models.stock import MedicineStock
from app.schemas.substitution import (
    CheckResult,
    CheckStatus,
    DecisionResult,
    DecisionStatus,
    RiskLevel,
    SubstitutionRequest,
)
from app.services.substitution_engine import (
    evaluate_age_check,
    evaluate_approved_alternative_check,
    evaluate_dosage_check,
    evaluate_drug_interaction_check,
    evaluate_hepatic_check,
    evaluate_patient_allergy_check,
    evaluate_pregnancy_check,
    evaluate_renal_check,
    evaluate_stock_check,
)


@dataclass
class CandidateEvaluation:
    """Evaluation result container for a single candidate alternative medicine."""

    candidate: MedicineAlternative
    checks: List[CheckResult]
    is_safe: bool
    risk_level: RiskLevel
    usable_stock_quantity: int

    def sort_key(self) -> Tuple[int, int, int, str, int]:
        """Deterministic priority sort key tuple:
        1. Safety (is_safe == True comes before False: 0 before 1)
        2. Lower overall risk level (LOW < MEDIUM < HIGH < CRITICAL: 0 < 1 < 2 < 3)
        3. Greater stock availability (-usable_stock_quantity)
        4. Alphabetical medicine-name ordering (lowercase ascending)
        5. MedicineAlternative.id ascending as final tie-breaker
        """
        risk_map = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        alt_name = getattr(self.candidate, "alternative_medicine", "") or ""
        alt_id = getattr(self.candidate, "id", 0) or 0
        return (
            0 if self.is_safe else 1,
            risk_map.get(self.risk_level, 0),
            -self.usable_stock_quantity,
            alt_name.strip().lower(),
            alt_id,
        )


def evaluate_single_candidate(
    request: SubstitutionRequest,
    candidate: MedicineAlternative,
    all_candidates: List[MedicineAlternative],
    patient: Optional[Patient] = None,
    patient_exists: bool = True,
    allergies: Optional[List[Allergy]] = None,
    clinical_constraints: Optional[List[ClinicalConstraint]] = None,
    prescribed_medications: Optional[List[PrescriptionMedication]] = None,
    prescribed_medication: Optional[PrescriptionMedication] = None,
    stock_records: Optional[List[MedicineStock]] = None,
    current_date: Optional[date] = None,
) -> CandidateEvaluation:
    """Evaluate all 9 safety checks in strict pipeline order for a single candidate alternative."""
    lookup_check = evaluate_approved_alternative_check(
        request.original_medicine, all_candidates
    )

    has_patient = (patient is not None) or (patient_exists is True)
    allergy_list = allergies if allergies is not None else []
    constraint_list = (
        clinical_constraints if clinical_constraints is not None else []
    )
    meds_list = (
        prescribed_medications if prescribed_medications is not None else []
    )
    target_med = prescribed_medication or (
        meds_list[0] if meds_list else None
    )
    stock_list = stock_records if stock_records is not None else []

    allergy_check = evaluate_patient_allergy_check(
        patient_exists=has_patient,
        allergies=allergy_list,
        alternative_medicine=candidate.alternative_medicine,
        alternative_ingredient=candidate.alternative_ingredient,
    )

    renal_check = evaluate_renal_check(
        patient_exists=has_patient,
        renal_status=patient.renal_status if patient else None,
        candidate_medicine=candidate.alternative_medicine,
        constraints=constraint_list,
    )

    hepatic_check = evaluate_hepatic_check(
        patient_exists=has_patient,
        hepatic_status=patient.hepatic_status if patient else None,
        candidate_medicine=candidate.alternative_medicine,
        constraints=constraint_list,
    )

    pregnancy_check = evaluate_pregnancy_check(
        patient_exists=has_patient,
        pregnancy_status=patient.pregnancy_status if patient else None,
        candidate_medicine=candidate.alternative_medicine,
        constraints=constraint_list,
    )

    age_check = evaluate_age_check(
        patient_exists=has_patient,
        patient_age=patient.age if patient else None,
        candidate_medicine=candidate.alternative_medicine,
        constraints=constraint_list,
    )

    interaction_check = evaluate_drug_interaction_check(
        patient_exists=has_patient,
        prescribed_medications=meds_list,
        candidate_medicine=candidate.alternative_medicine,
        constraints=constraint_list,
    )

    dosage_check = evaluate_dosage_check(
        patient_exists=has_patient,
        prescribed_medication=target_med,
        candidate_medicine=candidate.alternative_medicine,
        constraints=constraint_list,
    )

    stock_check = evaluate_stock_check(
        candidate_medicine=candidate.alternative_medicine,
        stock_records=stock_list,
        current_date=current_date,
    )

    checks_list = [
        lookup_check,
        allergy_check,
        renal_check,
        hepatic_check,
        pregnancy_check,
        age_check,
        interaction_check,
        dosage_check,
        stock_check,
    ]

    failed_checks = [c for c in checks_list if c.status == CheckStatus.FAIL]
    is_safe = (len(failed_checks) == 0)

    if failed_checks:
        risk_level = max(
            [c.severity for c in failed_checks], key=lambda s: s.value
        )
    else:
        risk_level = RiskLevel.LOW

    today = current_date or date.today()
    usable_stock_qty = sum(
        s.quantity_available
        for s in stock_list
        if s.is_available is True
        and s.quantity_available > 0
        and (s.expiry_date is None or s.expiry_date >= today)
    )

    return CandidateEvaluation(
        candidate=candidate,
        checks=checks_list,
        is_safe=is_safe,
        risk_level=risk_level,
        usable_stock_quantity=usable_stock_qty,
    )


def rank_and_select_candidate(
    request: SubstitutionRequest,
    evaluations: List[CandidateEvaluation],
) -> DecisionResult:
    """Deterministically rank candidate evaluations and select the safest best alternative."""
    if not evaluations:
        lookup_check = evaluate_approved_alternative_check(
            request.original_medicine, []
        )
        return DecisionResult(
            decision_status=DecisionStatus.NO_ALTERNATIVE,
            original_medicine=request.original_medicine,
            recommended_medicine=None,
            reason="No active approved alternative was found for the requested medicine.",
            risk_level=RiskLevel.LOW,
            requires_human_confirmation=False,
            confidence_score=1.0,
            checks=[lookup_check],
        )

    # Sort evaluations using deterministic sort_key
    sorted_evals = sorted(evaluations, key=lambda e: e.sort_key())

    safe_evals = [e for e in sorted_evals if e.is_safe]

    if safe_evals:
        best = safe_evals[0]
        n_eval = len(evaluations)
        n_safe = len(safe_evals)
        n_failed = n_eval - n_safe

        reason = (
            f"Selected candidate '{best.candidate.alternative_medicine}' out of {n_eval} "
            f"evaluated alternative(s). {n_safe} passed all safety checks and {n_failed} were excluded due to safety failures."
        )

        return DecisionResult(
            decision_status=DecisionStatus.RECOMMENDED,
            original_medicine=request.original_medicine,
            recommended_medicine=best.candidate.alternative_medicine,
            reason=reason,
            risk_level=RiskLevel.LOW,
            requires_human_confirmation=True,
            confidence_score=1.0,
            checks=best.checks,
        )

    # Case C: All candidates failed one or more safety checks
    first_eval = sorted_evals[0]
    failed_checks_across_all = [
        chk for e in evaluations for chk in e.checks if chk.status == CheckStatus.FAIL
    ]

    if failed_checks_across_all:
        max_severity = max(
            [c.severity for c in failed_checks_across_all], key=lambda s: s.value
        )
        primary_fail_reason = failed_checks_across_all[0].reason
    else:
        max_severity = RiskLevel.HIGH
        primary_fail_reason = "Safety checks failed."

    reason = (
        f"All {len(evaluations)} approved candidate alternative(s) failed safety evaluation and were excluded. "
        f"Primary blocking reason: {primary_fail_reason}"
    )

    return DecisionResult(
        decision_status=DecisionStatus.BLOCKED,
        original_medicine=request.original_medicine,
        recommended_medicine=None,
        reason=reason,
        risk_level=max_severity,
        requires_human_confirmation=True,
        confidence_score=1.0,
        checks=first_eval.checks,
    )
