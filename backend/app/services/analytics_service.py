"""Analytics and Decision Listing Service."""

from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories import compute_analytics_summary, query_substitution_decisions
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    DecisionListResponse,
    SafetyBlockBreakdown,
)
from app.services.substitution_service import get_substitution_decision_service


def list_substitution_decisions_service(
    db: Session,
    patient_id: Optional[int] = None,
    decision_status: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> DecisionListResponse:
    """Service to list and filter substitution decisions with pagination."""
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Limit parameter must be between 1 and 100.",
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Offset parameter must be greater than or equal to 0.",
        )

    db_items, total = query_substitution_decisions(
        db,
        patient_id=patient_id,
        decision_status=decision_status,
        risk_level=risk_level,
        limit=limit,
        offset=offset,
    )

    items = [get_substitution_decision_service(db, item.id) for item in db_items]

    return DecisionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


def get_analytics_summary_service(db: Session) -> AnalyticsSummaryResponse:
    """Service to retrieve real-time aggregate clinical decision analytics summary."""
    data = compute_analytics_summary(db)
    breakdown_data = data.get("safety_block_breakdown", {})
    safety_breakdown = SafetyBlockBreakdown(**breakdown_data)

    return AnalyticsSummaryResponse(
        total_decisions_evaluated=data.get("total_decisions_evaluated", 0),
        status_distribution=data.get("status_distribution", {}),
        risk_level_distribution=data.get("risk_level_distribution", {}),
        safety_block_breakdown=safety_breakdown,
        total_pharmacist_reviews=data.get("total_pharmacist_reviews", 0),
        total_pharmacist_overrides=data.get("total_pharmacist_overrides", 0),
    )
