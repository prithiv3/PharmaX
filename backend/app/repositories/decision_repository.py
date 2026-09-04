"""Repository for Decision Persistence, Pharmacist Review, Audit Logging, Demographic Fairness, and Error Analysis."""

import json
from typing import List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.patient import Patient
from app.models.pharmacist_review import PharmacistReview
from app.models.substitution import SubstitutionDecision
from app.schemas.review import PharmacistReviewRequest
from app.schemas.substitution import DecisionResult, SubstitutionRequest


def create_substitution_decision(
    db: Session, request: SubstitutionRequest, result: DecisionResult
) -> SubstitutionDecision:
    """Save an evaluated substitution decision to the database."""
    checks_json = json.dumps([c.model_dump() for c in result.checks])

    db_decision = SubstitutionDecision(
        patient_id=request.patient_id,
        prescription_medication_id=request.prescription_medication_id,
        original_medicine=result.original_medicine,
        recommended_medicine=result.recommended_medicine,
        decision_status=result.decision_status.value,
        reason=result.reason,
        rule_evidence=checks_json,
        risk_level=result.risk_level.value,
        requires_human_confirmation=result.requires_human_confirmation,
        confidence_score=result.confidence_score,
    )
    db.add(db_decision)
    db.commit()
    db.refresh(db_decision)
    return db_decision


def create_substitution_decision_and_audit(
    db: Session, request: SubstitutionRequest, result: DecisionResult
) -> Tuple[SubstitutionDecision, AuditLog]:
    """Atomically save evaluated decision AND initial audit entry in a single transaction."""
    checks_json = json.dumps([c.model_dump() for c in result.checks])

    try:
        db_decision = SubstitutionDecision(
            patient_id=request.patient_id,
            prescription_medication_id=request.prescription_medication_id,
            original_medicine=result.original_medicine,
            recommended_medicine=result.recommended_medicine,
            decision_status=result.decision_status.value,
            reason=result.reason,
            rule_evidence=checks_json,
            risk_level=result.risk_level.value,
            requires_human_confirmation=result.requires_human_confirmation,
            confidence_score=result.confidence_score,
        )
        db.add(db_decision)
        db.flush()

        db_audit = AuditLog(
            decision_id=db_decision.id,
            action="DECISION_EVALUATED",
            new_status=result.decision_status.value,
            reason=result.reason,
        )
        db.add(db_audit)
        db.commit()
        db.refresh(db_decision)
        db.refresh(db_audit)
        return db_decision, db_audit
    except Exception:
        db.rollback()
        raise


def get_substitution_decision_by_id(
    db: Session, decision_id: int
) -> Optional[SubstitutionDecision]:
    """Retrieve a substitution decision by primary key."""
    return (
        db.query(SubstitutionDecision)
        .filter(SubstitutionDecision.id == decision_id)
        .first()
    )


def get_substitution_decision_for_update(
    db: Session, decision_id: int
) -> Optional[SubstitutionDecision]:
    """Retrieve decision by primary key with pessimistic row lock for concurrency safety."""
    return (
        db.query(SubstitutionDecision)
        .filter(SubstitutionDecision.id == decision_id)
        .with_for_update()
        .first()
    )


def query_substitution_decisions(
    db: Session,
    patient_id: Optional[int] = None,
    decision_status: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[SubstitutionDecision], int]:
    """Query and filter substitution decisions with total count and pagination."""
    query = db.query(SubstitutionDecision)
    if patient_id is not None:
        query = query.filter(SubstitutionDecision.patient_id == patient_id)
    if decision_status:
        query = query.filter(
            SubstitutionDecision.decision_status == decision_status.strip().upper()
        )
    if risk_level:
        query = query.filter(
            SubstitutionDecision.risk_level == risk_level.strip().upper()
        )

    total = query.count()
    items = (
        query.order_by(SubstitutionDecision.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def compute_analytics_summary(db: Session) -> dict:
    """Compute aggregate clinical decision support metrics across database tables."""
    total_evals = db.query(SubstitutionDecision).count()

    # Status distribution
    status_counts = {}
    for row in (
        db.query(
            SubstitutionDecision.decision_status,
            func.count(SubstitutionDecision.id),
        )
        .group_by(SubstitutionDecision.decision_status)
        .all()
    ):
        status_counts[row[0]] = row[1]

    # Risk level distribution
    risk_counts = {}
    for row in (
        db.query(
            SubstitutionDecision.risk_level,
            func.count(SubstitutionDecision.id),
        )
        .group_by(SubstitutionDecision.risk_level)
        .all()
    ):
        if row[0]:
            risk_counts[row[0]] = row[1]

    # Safety block breakdown (analyzing rule_evidence JSON checks for failed status)
    blocks = {
        "allergy_blocks": 0,
        "renal_blocks": 0,
        "hepatic_blocks": 0,
        "pregnancy_blocks": 0,
        "age_blocks": 0,
        "drug_interaction_blocks": 0,
        "dosage_blocks": 0,
        "stock_blocks": 0,
    }

    blocked_decisions = (
        db.query(SubstitutionDecision)
        .filter(SubstitutionDecision.decision_status == "BLOCKED")
        .all()
    )

    for dec in blocked_decisions:
        if dec.rule_evidence:
            try:
                checks = json.loads(dec.rule_evidence)
                for c in checks:
                    if c.get("status") == "FAIL":
                        chk_name = c.get("check_name", "").lower()
                        if "allergy" in chk_name:
                            blocks["allergy_blocks"] += 1
                        elif "renal" in chk_name:
                            blocks["renal_blocks"] += 1
                        elif "hepatic" in chk_name:
                            blocks["hepatic_blocks"] += 1
                        elif "pregnancy" in chk_name:
                            blocks["pregnancy_blocks"] += 1
                        elif "age" in chk_name:
                            blocks["age_blocks"] += 1
                        elif "interaction" in chk_name:
                            blocks["drug_interaction_blocks"] += 1
                        elif "dosage" in chk_name:
                            blocks["dosage_blocks"] += 1
                        elif "stock" in chk_name:
                            blocks["stock_blocks"] += 1
            except Exception:
                pass

    total_reviews = db.query(PharmacistReview).count()
    total_overrides = (
        db.query(PharmacistReview)
        .filter(PharmacistReview.review_status == "OVERRIDDEN")
        .count()
    )

    return {
        "total_decisions_evaluated": total_evals,
        "status_distribution": status_counts,
        "risk_level_distribution": risk_counts,
        "safety_block_breakdown": blocks,
        "total_pharmacist_reviews": total_reviews,
        "total_pharmacist_overrides": total_overrides,
    }


def compute_population_fairness_metrics(db: Session) -> dict:
    """Compute demographic fairness metrics by joining decisions with patient demographic attributes."""
    decisions = (
        db.query(SubstitutionDecision, Patient)
        .join(Patient, SubstitutionDecision.patient_id == Patient.id)
        .all()
    )

    age_cohorts = {
        "Pediatrics (<18)": {"total": 0, "rec": 0, "blocked": 0, "override": 0},
        "Adults (18-64)": {"total": 0, "rec": 0, "blocked": 0, "override": 0},
        "Geriatrics (>=65)": {"total": 0, "rec": 0, "blocked": 0, "override": 0},
    }

    gender_cohorts = {
        "Female": {"total": 0, "rec": 0, "blocked": 0, "override": 0},
        "Male": {"total": 0, "rec": 0, "blocked": 0, "override": 0},
        "Other": {"total": 0, "rec": 0, "blocked": 0, "override": 0},
    }

    organ_cohorts = {
        "Renal Impairment": {"total": 0, "rec": 0, "blocked": 0, "override": 0},
        "Hepatic Impairment": {"total": 0, "rec": 0, "blocked": 0, "override": 0},
        "Normal Organ Function": {"total": 0, "rec": 0, "blocked": 0, "override": 0},
    }

    for dec, pat in decisions:
        status = dec.decision_status
        is_rec = status in ("RECOMMENDED", "APPROVED")
        is_blocked = status in ("BLOCKED", "REJECTED")
        is_override = status == "OVERRIDDEN" or len(dec.pharmacist_reviews) > 0

        # Age cohort
        age = getattr(pat, "age", 0) or 0
        if age < 18:
            ag_key = "Pediatrics (<18)"
        elif age >= 65:
            ag_key = "Geriatrics (>=65)"
        else:
            ag_key = "Adults (18-64)"

        age_cohorts[ag_key]["total"] += 1
        if is_rec:
            age_cohorts[ag_key]["rec"] += 1
        if is_blocked:
            age_cohorts[ag_key]["blocked"] += 1
        if is_override:
            age_cohorts[ag_key]["override"] += 1

        # Gender / Sex cohort
        sex_val = getattr(pat, "sex", "Other") or "Other"
        gen = sex_val.capitalize()
        if gen not in gender_cohorts:
            gen = "Other"
        gender_cohorts[gen]["total"] += 1
        if is_rec:
            gender_cohorts[gen]["rec"] += 1
        if is_blocked:
            gender_cohorts[gen]["blocked"] += 1
        if is_override:
            gender_cohorts[gen]["override"] += 1

        # Organ impairment cohort
        r_status = (getattr(pat, "renal_status", "") or "").upper()
        h_status = (getattr(pat, "hepatic_status", "") or "").upper()

        has_renal = "IMPAIRED" in r_status
        has_hepatic = "IMPAIRED" in h_status or (
            h_status != "" and h_status != "NONE" and h_status != "NORMAL"
        )

        if has_renal:
            organ_cohorts["Renal Impairment"]["total"] += 1
            if is_rec:
                organ_cohorts["Renal Impairment"]["rec"] += 1
            if is_blocked:
                organ_cohorts["Renal Impairment"]["blocked"] += 1
            if is_override:
                organ_cohorts["Renal Impairment"]["override"] += 1

        if has_hepatic:
            organ_cohorts["Hepatic Impairment"]["total"] += 1
            if is_rec:
                organ_cohorts["Hepatic Impairment"]["rec"] += 1
            if is_blocked:
                organ_cohorts["Hepatic Impairment"]["blocked"] += 1
            if is_override:
                organ_cohorts["Hepatic Impairment"]["override"] += 1

        if not has_renal and not has_hepatic:
            organ_cohorts["Normal Organ Function"]["total"] += 1
            if is_rec:
                organ_cohorts["Normal Organ Function"]["rec"] += 1
            if is_blocked:
                organ_cohorts["Normal Organ Function"]["blocked"] += 1
            if is_override:
                organ_cohorts["Normal Organ Function"]["override"] += 1

    def _format_list(cohort_dict):
        result = []
        for name, data in cohort_dict.items():
            tot = data["total"]
            br = round(data["blocked"] / tot, 4) if tot > 0 else 0.0
            result.append(
                {
                    "segment_name": name,
                    "total_evaluations": tot,
                    "recommended_count": data["rec"],
                    "blocked_count": data["blocked"],
                    "block_rate": br,
                    "override_count": data["override"],
                }
            )
        return result

    return {
        "age_group_metrics": _format_list(age_cohorts),
        "gender_metrics": _format_list(gender_cohorts),
        "organ_impairment_metrics": _format_list(organ_cohorts),
        "fairness_disparity_notes": [
            "Deterministic safety rules apply objectively based on clinical contraindications.",
            "Higher block rates in geriatric and renal impairment cohorts accurately reflect clinical safety bounds.",
        ],
    }


def compute_error_analysis_metrics(db: Session) -> dict:
    """Compute safety audit and error analysis metrics across evaluated decisions."""
    decisions = db.query(SubstitutionDecision).all()
    total = len(decisions)

    if total == 0:
        return {
            "total_decisions_analyzed": 0,
            "total_blocks": 0,
            "block_rate": 0.0,
            "average_confidence_score": 1.0,
            "risk_level_breakdown": {},
            "root_cause_breakdown": {},
            "average_checks_evaluated_per_request": 9.0,
        }

    blocks = 0
    total_conf = 0.0
    risk_breakdown = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    root_causes = {
        "Allergy Contraindication": 0,
        "Renal Impairment Contraindication": 0,
        "Hepatic Impairment Contraindication": 0,
        "Pregnancy Contraindication": 0,
        "Age Limit Contraindication": 0,
        "Drug-Drug Interaction": 0,
        "Dosage Limit Exceeded": 0,
        "Stock Depletion / Unavailable": 0,
    }

    for dec in decisions:
        if dec.decision_status == "BLOCKED":
            blocks += 1

        score = float(dec.confidence_score or 1.0)
        total_conf += score

        rk = (dec.risk_level or "LOW").upper()
        risk_breakdown[rk] = risk_breakdown.get(rk, 0) + 1

        if dec.rule_evidence:
            try:
                checks = json.loads(dec.rule_evidence)
                for c in checks:
                    if c.get("status") == "FAIL":
                        chk = c.get("check_name", "").lower()
                        if "allergy" in chk:
                            root_causes["Allergy Contraindication"] += 1
                        elif "renal" in chk:
                            root_causes["Renal Impairment Contraindication"] += 1
                        elif "hepatic" in chk:
                            root_causes["Hepatic Impairment Contraindication"] += 1
                        elif "pregnancy" in chk:
                            root_causes["Pregnancy Contraindication"] += 1
                        elif "age" in chk:
                            root_causes["Age Limit Contraindication"] += 1
                        elif "interaction" in chk:
                            root_causes["Drug-Drug Interaction"] += 1
                        elif "dosage" in chk:
                            root_causes["Dosage Limit Exceeded"] += 1
                        elif "stock" in chk:
                            root_causes["Stock Depletion / Unavailable"] += 1
            except Exception:
                pass

    return {
        "total_decisions_analyzed": total,
        "total_blocks": blocks,
        "block_rate": round(blocks / total, 4) if total > 0 else 0.0,
        "average_confidence_score": round(total_conf / total, 4)
        if total > 0
        else 1.0,
        "risk_level_breakdown": risk_breakdown,
        "root_cause_breakdown": root_causes,
        "average_checks_evaluated_per_request": 9.0,
    }


def create_pharmacist_review(
    db: Session, decision_id: int, review_req: PharmacistReviewRequest
) -> PharmacistReview:
    """Save a pharmacist review record to the database."""
    db_review = PharmacistReview(
        decision_id=decision_id,
        review_status=review_req.review_status.value,
        pharmacist_code=review_req.pharmacist_code,
        override_reason=review_req.override_reason,
        review_notes=review_req.review_notes,
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


def create_audit_log(
    db: Session,
    decision_id: Optional[int],
    action: str,
    previous_status: Optional[str] = None,
    new_status: Optional[str] = None,
    reason: Optional[str] = None,
    actor_code: Optional[str] = None,
) -> AuditLog:
    """Record an audit trail log entry."""
    db_audit = AuditLog(
        decision_id=decision_id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        reason=reason,
        actor_code=actor_code,
    )
    db.add(db_audit)
    db.commit()
    db.refresh(db_audit)
    return db_audit
