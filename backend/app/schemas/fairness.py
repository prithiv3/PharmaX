"""Population Bias, Fairness, and Error Analysis Schemas."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DemographicSegmentMetrics(BaseModel):
    segment_name: str = Field(..., description="Name of demographic cohort or segment")
    total_evaluations: int = Field(0, description="Total evaluations in this cohort")
    recommended_count: int = Field(0, description="Recommended substitution count")
    blocked_count: int = Field(0, description="Blocked decision count")
    block_rate: float = Field(0.0, description="Ratio of blocked decisions to total evaluations")
    override_count: int = Field(0, description="Pharmacist override count in this cohort")


class PopulationFairnessResponse(BaseModel):
    age_group_metrics: List[DemographicSegmentMetrics] = Field(default_factory=list)
    gender_metrics: List[DemographicSegmentMetrics] = Field(default_factory=list)
    organ_impairment_metrics: List[DemographicSegmentMetrics] = Field(default_factory=list)
    fairness_disparity_notes: List[str] = Field(default_factory=list)


class ErrorAnalysisResponse(BaseModel):
    total_decisions_analyzed: int = Field(0, description="Total decisions analyzed")
    total_blocks: int = Field(0, description="Total blocked decisions")
    block_rate: float = Field(0.0, description="Overall safety block rate")
    average_confidence_score: float = Field(1.0, description="Mean decision confidence score")
    risk_level_breakdown: Dict[str, int] = Field(default_factory=dict)
    root_cause_breakdown: Dict[str, int] = Field(default_factory=dict)
    average_checks_evaluated_per_request: float = Field(9.0, description="Average safety checks evaluated")
