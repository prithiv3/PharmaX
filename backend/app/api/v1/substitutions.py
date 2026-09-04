from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.analytics import AnalyticsSummaryResponse, DecisionListResponse
from app.schemas.fairness import ErrorAnalysisResponse, PopulationFairnessResponse
from app.schemas.review import (
    PharmacistReviewRequest,
    SubstitutionDecisionDetailResponse,
)
from app.schemas.substitution import (
    DecisionResult,
    PresetLookupResponse,
    SubstitutionRequest,
)
from app.services.analytics_service import (
    get_analytics_summary_service,
    list_substitution_decisions_service,
)
from app.services.fairness_service import (
    get_error_analysis_service,
    get_population_fairness_service,
)
from app.services.substitution_service import (
    evaluate_substitution_request_service,
    get_substitution_decision_service,
    lookup_preset_by_code_service,
    submit_pharmacist_review_service,
)

router = APIRouter(prefix="/api/v1/substitutions", tags=["Substitutions"])


@router.post(
    "/evaluate",
    response_model=DecisionResult,
    status_code=status.HTTP_200_OK,
    summary="Evaluate pharmacy substitution decision support request",
    description="Deterministically evaluates patient, clinical, allergy, interaction, dosage, and stock safety constraints for a proposed substitution.",
)
def evaluate_substitution(
    request: SubstitutionRequest, db: Session = Depends(get_db)
) -> DecisionResult:
    """Evaluate substitution decision request through service layer and decision engine."""
    try:
        return evaluate_substitution_request_service(db, request)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during substitution evaluation.",
        ) from exc


@router.get(
    "/preset-lookup/{patient_code}/{prescription_code}",
    response_model=PresetLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Lookup patient and prescription database IDs by business codes",
    description="Resolves current PostgreSQL primary key IDs for a given patient code and prescription code.",
)
def lookup_preset_by_code(
    patient_code: str, prescription_code: str, db: Session = Depends(get_db)
) -> PresetLookupResponse:
    """Lookup current database IDs by patient_code and prescription_code."""
    try:
        return lookup_preset_by_code_service(db, patient_code, prescription_code)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during preset lookup.",
        ) from exc



@router.get(
    "",
    response_model=DecisionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Query and filter substitution decisions",
    description="Lists persisted substitution decision records with filtering by patient, status, risk level, and pagination parameters.",
)
def list_substitution_decisions(
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    decision_status: Optional[str] = Query(None, description="Filter by decision status"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(20, ge=1, le=100, description="Limit count of items"),
    offset: int = Query(0, ge=0, description="Offset count of items"),
    db: Session = Depends(get_db),
) -> DecisionListResponse:
    """Query and filter substitution decisions."""
    try:
        return list_substitution_decisions_service(
            db,
            patient_id=patient_id,
            decision_status=decision_status,
            risk_level=risk_level,
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while querying substitution decisions.",
        ) from exc


@router.get(
    "/analytics/summary",
    response_model=AnalyticsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get real-time decision support analytics summary",
    description="Computes aggregate clinical decision metrics including safety block category breakdowns, risk distributions, and override statistics.",
)
def get_analytics_summary(
    db: Session = Depends(get_db)
) -> AnalyticsSummaryResponse:
    """Retrieve decision support analytics summary."""
    try:
        return get_analytics_summary_service(db)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while computing analytics summary.",
        ) from exc


@router.get(
    "/analytics/fairness",
    response_model=PopulationFairnessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get synthetic population demographic bias and fairness metrics",
    description="Evaluates decision outcome distributions across age cohorts, gender, and organ impairment demographic segments.",
)
def get_population_fairness(
    db: Session = Depends(get_db)
) -> PopulationFairnessResponse:
    """Retrieve population demographic bias and fairness metrics."""
    try:
        return get_population_fairness_service(db)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while computing population fairness metrics.",
        ) from exc


@router.get(
    "/analytics/error-analysis",
    response_model=ErrorAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get safety audit and error analysis metrics",
    description="Computes safety block root cause distributions, risk severity breakdowns, and decision confidence averages.",
)
def get_error_analysis(
    db: Session = Depends(get_db)
) -> ErrorAnalysisResponse:
    """Retrieve safety audit and error analysis metrics."""
    try:
        return get_error_analysis_service(db)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while computing error analysis metrics.",
        ) from exc


@router.get(
    "/{decision_id}",
    response_model=SubstitutionDecisionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get persisted substitution decision details",
    description="Retrieves a persisted substitution decision record by ID, including evidence checks and review history.",
)
def get_substitution_decision(
    decision_id: int, db: Session = Depends(get_db)
) -> SubstitutionDecisionDetailResponse:
    """Retrieve decision record detail by ID."""
    try:
        return get_substitution_decision_service(db, decision_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while retrieving decision details.",
        ) from exc


from app.core.security import get_authenticated_pharmacist


@router.post(
    "/{decision_id}/review",
    response_model=SubstitutionDecisionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit pharmacist review, approval, or override for a decision",
    description="Records a licensed pharmacist's confirmation, rejection, or clinical override for a substitution decision. Requires prototype pharmacist token header (X-Pharmacist-Token).",
)
def submit_pharmacist_review(
    decision_id: int,
    review_request: PharmacistReviewRequest,
    authenticated_pharmacist: str = Depends(get_authenticated_pharmacist),
    db: Session = Depends(get_db),
) -> SubstitutionDecisionDetailResponse:
    """Submit pharmacist review/override for a decision."""
    try:
        return submit_pharmacist_review_service(
            db,
            decision_id,
            review_request,
            authenticated_pharmacist=authenticated_pharmacist,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while processing pharmacist review.",
        ) from exc
