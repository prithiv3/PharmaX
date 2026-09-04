"""Analytics and Decision Query Schemas."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.review import SubstitutionDecisionDetailResponse


class DecisionListResponse(BaseModel):
    total: int = Field(..., description="Total count of matching decision records")
    limit: int = Field(..., description="Query limit page size")
    offset: int = Field(..., description="Query offset position")
    items: List[SubstitutionDecisionDetailResponse] = Field(
        default_factory=list, description="List of decision detail items"
    )


class SafetyBlockBreakdown(BaseModel):
    allergy_blocks: int = 0
    renal_blocks: int = 0
    hepatic_blocks: int = 0
    pregnancy_blocks: int = 0
    age_blocks: int = 0
    drug_interaction_blocks: int = 0
    dosage_blocks: int = 0
    stock_blocks: int = 0


class AnalyticsSummaryResponse(BaseModel):
    total_decisions_evaluated: int
    status_distribution: Dict[str, int]
    risk_level_distribution: Dict[str, int]
    safety_block_breakdown: SafetyBlockBreakdown
    total_pharmacist_reviews: int
    total_pharmacist_overrides: int
