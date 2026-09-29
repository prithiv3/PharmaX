"""Population Bias, Fairness, and Error Analysis Schemas.

Extended to carry baseline metrics and formal statistical-parity /
error-rate disparity fields required by the demographic bias analysis
milestone.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Per-cohort metrics
# ---------------------------------------------------------------------------

class DemographicSegmentMetrics(BaseModel):
    """Metrics for a single demographic cohort (age group, gender, organ status)."""

    segment_name: str = Field(..., description="Name of demographic cohort or segment")

    # Volume counts
    total_evaluations: int = Field(0, description="Total evaluations in this cohort")
    recommended_count: int = Field(0, description="Recommended substitution count")
    blocked_count: int = Field(0, description="Blocked decision count")
    override_count: int = Field(0, description="Pharmacist override count in this cohort")

    # Primary rates
    block_rate: float = Field(
        0.0,
        description=(
            "Safety block rate = blocked / total (0.0-1.0). "
            "Equivalent to the False-Omission-Rate proxy for this cohort."
        ),
    )
    approval_rate: float = Field(
        0.0,
        description="Recommendation / approval rate = recommended / total (0.0-1.0)",
    )
    override_rate: float = Field(
        0.0,
        description="Override rate = overrides / total (0.0-1.0)",
    )

    # Baseline & disparity metrics (formal bias reporting)
    baseline_block_rate: Optional[float] = Field(
        None,
        description=(
            "Population-wide baseline block rate across ALL cohorts combined. "
            "Provided for direct comparison against this segment's block_rate."
        ),
    )
    statistical_parity_gap: Optional[float] = Field(
        None,
        description=(
            "Statistical Parity Gap = this cohort block_rate - baseline_block_rate. "
            "Positive: cohort blocked MORE than population baseline. "
            "Negative: cohort blocked LESS than population baseline. "
            "Values beyond +/-0.05 warrant clinical governance review."
        ),
    )
    error_rate_disparity: Optional[float] = Field(
        None,
        description=(
            "Error-Rate Disparity = this cohort block_rate / baseline_block_rate. "
            "Ratio > 1.0 indicates disproportionate safety blocking. "
            "Ratio < 1.0 indicates under-blocking relative to population average. "
            "Null when baseline block rate is zero."
        ),
    )
    max_intra_dimension_gap: Optional[float] = Field(
        None,
        description=(
            "Maximum absolute block-rate difference between this segment and any other "
            "segment within the same demographic dimension (age / gender / organ). "
            "High values flag potential systematic disparities within a dimension."
        ),
    )


# ---------------------------------------------------------------------------
# Cross-cohort bias audit summary
# ---------------------------------------------------------------------------

class BiasAuditSummary(BaseModel):
    """Aggregate bias audit statistics derived from all demographic dimensions."""

    population_baseline_block_rate: float = Field(
        0.0,
        description="Overall block rate across the entire evaluated population.",
    )
    population_baseline_approval_rate: float = Field(
        0.0,
        description="Overall recommendation/approval rate across the entire population.",
    )
    population_baseline_override_rate: float = Field(
        0.0,
        description="Overall pharmacist override rate across the entire population.",
    )

    max_age_parity_gap: float = Field(
        0.0,
        description="Maximum |statistical parity gap| across age cohorts.",
    )
    max_gender_parity_gap: float = Field(
        0.0,
        description="Maximum |statistical parity gap| across gender cohorts.",
    )
    max_organ_parity_gap: float = Field(
        0.0,
        description="Maximum |statistical parity gap| across organ-impairment cohorts.",
    )

    max_age_error_rate_disparity: Optional[float] = Field(
        None,
        description="Maximum error-rate disparity ratio across age cohorts.",
    )
    max_gender_error_rate_disparity: Optional[float] = Field(
        None,
        description="Maximum error-rate disparity ratio across gender cohorts.",
    )
    max_organ_error_rate_disparity: Optional[float] = Field(
        None,
        description="Maximum error-rate disparity ratio across organ-impairment cohorts.",
    )

    fairness_threshold_breached: bool = Field(
        False,
        description=(
            "True if any cohort |statistical_parity_gap| > 0.05, "
            "indicating a disparity that exceeds the governance threshold."
        ),
    )
    breached_segments: List[str] = Field(
        default_factory=list,
        description="List of segment names where the fairness threshold was exceeded.",
    )


# ---------------------------------------------------------------------------
# Top-level response objects
# ---------------------------------------------------------------------------

class PopulationFairnessResponse(BaseModel):
    """Full demographic fairness analysis response with baseline and disparity metrics."""

    age_group_metrics: List[DemographicSegmentMetrics] = Field(default_factory=list)
    gender_metrics: List[DemographicSegmentMetrics] = Field(default_factory=list)
    organ_impairment_metrics: List[DemographicSegmentMetrics] = Field(default_factory=list)
    bias_audit_summary: Optional[BiasAuditSummary] = Field(
        None,
        description="Aggregate cross-cohort bias audit statistics and threshold breach flags.",
    )
    fairness_disparity_notes: List[str] = Field(default_factory=list)


class ErrorAnalysisResponse(BaseModel):
    """Safety audit and decision error analysis metrics."""

    total_decisions_analyzed: int = Field(0, description="Total decisions analyzed")
    total_blocks: int = Field(0, description="Total blocked decisions")
    block_rate: float = Field(0.0, description="Overall safety block rate")
    average_confidence_score: float = Field(1.0, description="Mean decision confidence score")
    risk_level_breakdown: Dict[str, int] = Field(default_factory=dict)
    root_cause_breakdown: Dict[str, int] = Field(default_factory=dict)
    average_checks_evaluated_per_request: float = Field(
        9.0, description="Average safety checks evaluated"
    )
