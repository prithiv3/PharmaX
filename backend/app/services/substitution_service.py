"""Substitution Service - Database retrieval, evaluation persistence, audit logging, and pharmacist review orchestration."""

import json
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.medication import PrescriptionMedication
from app.models.prescription import Prescription
from app.repositories import (
    create_audit_log,
    create_pharmacist_review,
    create_substitution_decision,
    create_substitution_decision_and_audit,
    get_active_alternatives_for_medicine,
    get_active_clinical_constraints,
    get_patient_allergies,
    get_patient_by_id,
    get_patient_prescribed_medications,
    get_stock_records_for_medicine,
    get_substitution_decision_by_id,
    get_substitution_decision_for_update,
)
from app.schemas.review import (
    AuditLogResponse,
    PharmacistReviewRequest,
    PharmacistReviewResponse,
    ReviewStatus,
    SubstitutionDecisionDetailResponse,
)
from app.schemas.substitution import (
    CheckResult,
    DecisionResult,
    DecisionStatus,
    PresetLookupResponse,
    RiskLevel,
    SubstitutionRequest,
)
from app.services.substitution_engine import evaluate_substitution_lookup


def evaluate_substitution_request_service(
    db: Session, request: SubstitutionRequest
) -> DecisionResult:
    """Orchestrate database validation, candidate ranking, and decision persistence."""
    # 1. Verify patient existence
    patient = get_patient_by_id(db, request.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found.",
        )

    # 2. Verify prescription existence
    prescription = (
        db.query(Prescription)
        .filter(Prescription.id == request.prescription_id)
        .first()
    )
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription record not found.",
        )

    # 3. Verify prescription medication existence
    medication = (
        db.query(PrescriptionMedication)
        .filter(
            PrescriptionMedication.id == request.prescription_medication_id
        )
        .first()
    )
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription medication record not found.",
        )

    # 4. Verify medication belongs to supplied prescription
    if medication.prescription_id != request.prescription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prescription medication does not belong to the supplied prescription.",
        )

    # 5. Verify prescription belongs to supplied patient
    if prescription.patient_id != request.patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prescription does not belong to the supplied patient.",
        )

    # Determine requested/original medicine name
    target_medicine = request.original_medicine or medication.medicine_name
    active_alts = get_active_alternatives_for_medicine(db, target_medicine)

    # Handle requested alternative explicitly supplied by caller
    if request.requested_alternative and request.requested_alternative.strip():
        req_alt_norm = request.requested_alternative.strip().lower()
        matching_alt = next(
            (
                a
                for a in active_alts
                if a.alternative_medicine.strip().lower() == req_alt_norm
            ),
            None,
        )
        if matching_alt:
            candidates = [matching_alt] + [
                a for a in active_alts if a.id != matching_alt.id
            ]
        else:
            candidates = []
    else:
        candidates = active_alts

    # Retrieve patient clinical history & candidate rules
    allergies = get_patient_allergies(db, request.patient_id)
    prescribed_meds = get_patient_prescribed_medications(db, request.patient_id)

    if not candidates:
        eval_result = evaluate_substitution_lookup(
            request=request,
            candidates=[],
            patient=patient,
            allergies=allergies,
            prescribed_medications=prescribed_meds,
            prescribed_medication=medication,
        )
    else:
        from app.services.alternative_ranking import (
            evaluate_single_candidate,
            rank_and_select_candidate,
        )

        evaluations = []
        for cand in candidates:
            cand_constraints = get_active_clinical_constraints(
                db, cand.alternative_medicine
            )
            cand_stock = get_stock_records_for_medicine(
                db, cand.alternative_medicine
            )
            eval_res = evaluate_single_candidate(
                request=request,
                candidate=cand,
                all_candidates=candidates,
                patient=patient,
                allergies=allergies,
                clinical_constraints=cand_constraints,
                prescribed_medications=prescribed_meds,
                prescribed_medication=medication,
                stock_records=cand_stock,
            )
            evaluations.append(eval_res)

        eval_result = rank_and_select_candidate(request, evaluations)

    # Persist decision to database & create audit log entry atomically
    db_decision, _ = create_substitution_decision_and_audit(db, request, eval_result)

    return eval_result


def get_substitution_decision_service(
    db: Session, decision_id: int
) -> SubstitutionDecisionDetailResponse:
    """Retrieve decision record detail by ID."""
    db_decision = get_substitution_decision_by_id(db, decision_id)
    if not db_decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Substitution decision record not found.",
        )

    # Deserialize evidence checks JSON
    checks = []
    if db_decision.rule_evidence:
        try:
            raw_checks = json.loads(db_decision.rule_evidence)
            checks = [CheckResult(**c) for c in raw_checks]
        except Exception:
            checks = []

    # Map reviews & audit logs
    reviews = [
        PharmacistReviewResponse(
            id=r.id,
            decision_id=r.decision_id,
            pharmacist_code=r.pharmacist_code,
            review_status=r.review_status,
            override_reason=r.override_reason,
            review_notes=r.review_notes,
            reviewed_at=r.reviewed_at,
        )
        for r in db_decision.pharmacist_reviews
    ]

    audit_logs = [
        AuditLogResponse(
            id=a.id,
            decision_id=a.decision_id,
            action=a.action,
            previous_status=a.previous_status,
            new_status=a.new_status,
            reason=a.reason,
            actor_code=a.actor_code,
            created_at=a.created_at,
        )
        for a in db_decision.audit_logs
    ]

    # Map decision_status safely
    try:
        d_status = DecisionStatus(db_decision.decision_status)
    except ValueError:
        d_status = DecisionStatus.RECOMMENDED

    return SubstitutionDecisionDetailResponse(
        id=db_decision.id,
        decision_status=d_status,
        original_medicine=db_decision.original_medicine,
        recommended_medicine=db_decision.recommended_medicine,
        reason=db_decision.reason or "",
        risk_level=RiskLevel(db_decision.risk_level or "LOW"),
        requires_human_confirmation=db_decision.requires_human_confirmation,
        confidence_score=float(db_decision.confidence_score or 1.0),
        checks=checks,
        reviews=reviews,
        audit_logs=audit_logs,
        created_at=db_decision.created_at,
    )


def submit_pharmacist_review_service(
    db: Session,
    decision_id: int,
    review_req: PharmacistReviewRequest,
    authenticated_pharmacist: Optional[str] = None,
) -> SubstitutionDecisionDetailResponse:
    """Process pharmacist human-in-the-loop review confirmation or override with concurrency safety."""
    # Use pessimistic row locking for concurrency protection
    db_decision = get_substitution_decision_for_update(db, decision_id)
    if not db_decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Substitution decision record not found.",
        )

    # Use review_req.pharmacist_code if supplied, else fallback to authenticated pharmacist code
    pharmacist_code = (
        review_req.pharmacist_code
        if review_req.pharmacist_code and review_req.pharmacist_code.strip()
        else authenticated_pharmacist
    )
    review_req.pharmacist_code = pharmacist_code

    # Require non-empty override_reason if review_status is OVERRIDDEN
    if review_req.review_status == ReviewStatus.OVERRIDDEN:
        if not review_req.override_reason or not review_req.override_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An override reason is required when status is OVERRIDDEN.",
            )

    prev_status = db_decision.decision_status
    new_status = review_req.review_status.value

    # Save pharmacist review record
    create_pharmacist_review(db, decision_id, review_req)

    # Record audit log entry
    create_audit_log(
        db,
        decision_id=decision_id,
        action="PHARMACIST_REVIEW",
        previous_status=prev_status,
        new_status=new_status,
        reason=review_req.override_reason or review_req.review_notes or f"Pharmacist {pharmacist_code} submitted review",
        actor_code=pharmacist_code,
    )

    return get_substitution_decision_service(db, decision_id)


def lookup_preset_by_code_service(
    db: Session, patient_code: str, prescription_code: str
) -> PresetLookupResponse:
    """Lookup current PostgreSQL database primary key IDs for a given patient code and prescription code."""
    patient = db.query(Patient).filter(Patient.patient_code == patient_code).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient record not found for code '{patient_code}'.",
        )

    rx = db.query(Prescription).filter(Prescription.prescription_code == prescription_code).first()
    if not rx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription record not found for code '{prescription_code}'.",
        )

    if rx.patient_id != patient.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prescription '{prescription_code}' does not belong to patient '{patient_code}'.",
        )

    med = db.query(PrescriptionMedication).filter(PrescriptionMedication.prescription_id == rx.id).first()
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription medication record not found for prescription '{prescription_code}'.",
        )

    return PresetLookupResponse(
        patient_id=patient.id,
        patient_code=patient.patient_code,
        prescription_id=rx.id,
        prescription_code=rx.prescription_code,
        prescription_medication_id=med.id,
        medicine_name=med.medicine_name,
    )

