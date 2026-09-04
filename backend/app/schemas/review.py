"""Pharmacist Review and Decision Detail Schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.substitution import DecisionResult


class ReviewStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"


class PharmacistReviewRequest(BaseModel):
    pharmacist_code: str = Field(
        ..., description="Unique code/identifier of the reviewing pharmacist"
    )
    review_status: ReviewStatus = Field(
        ..., description="Action taken by pharmacist: APPROVED, REJECTED, or OVERRIDDEN"
    )
    override_reason: Optional[str] = Field(
        None, description="Justification required if status is OVERRIDDEN"
    )
    review_notes: Optional[str] = Field(
        None, description="Optional clinical review notes"
    )


class PharmacistReviewResponse(BaseModel):
    id: int
    decision_id: int
    pharmacist_code: Optional[str] = None
    review_status: str
    override_reason: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: datetime


class AuditLogResponse(BaseModel):
    id: int
    decision_id: Optional[int] = None
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    reason: Optional[str] = None
    actor_code: Optional[str] = None
    created_at: datetime


class SubstitutionDecisionDetailResponse(DecisionResult):
    id: int
    reviews: List[PharmacistReviewResponse] = Field(default_factory=list)
    audit_logs: List[AuditLogResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None
