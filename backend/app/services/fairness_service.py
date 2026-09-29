"""Demographic Fairness and Safety Audit Error Analysis Service."""

from sqlalchemy.orm import Session
from app.repositories import (
    compute_error_analysis_metrics,
    compute_population_fairness_metrics,
)
from app.schemas.fairness import (
    BiasAuditSummary,
    DemographicSegmentMetrics,
    ErrorAnalysisResponse,
    PopulationFairnessResponse,
)


def get_population_fairness_service(db: Session) -> PopulationFairnessResponse:
    """Service to compute demographic bias and fairness metrics across synthetic populations."""
    raw = compute_population_fairness_metrics(db)

    bias_raw = raw.get("bias_audit_summary", {})
    bias_summary = BiasAuditSummary(**bias_raw) if bias_raw else None

    return PopulationFairnessResponse(
        age_group_metrics=[
            DemographicSegmentMetrics(**m) for m in raw.get("age_group_metrics", [])
        ],
        gender_metrics=[
            DemographicSegmentMetrics(**m) for m in raw.get("gender_metrics", [])
        ],
        organ_impairment_metrics=[
            DemographicSegmentMetrics(**m)
            for m in raw.get("organ_impairment_metrics", [])
        ],
        bias_audit_summary=bias_summary,
        fairness_disparity_notes=raw.get("fairness_disparity_notes", []),
    )


def get_error_analysis_service(db: Session) -> ErrorAnalysisResponse:
    """Service to compute safety audit and decision error analysis metrics."""
    raw = compute_error_analysis_metrics(db)
    return ErrorAnalysisResponse(**raw)
