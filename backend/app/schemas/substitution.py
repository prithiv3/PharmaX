from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DecisionStatus(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    BLOCKED = "BLOCKED"
    NO_ALTERNATIVE = "NO_ALTERNATIVE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_CHECKED = "NOT_CHECKED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CheckResult(BaseModel):
    check_name: str
    status: CheckStatus
    reason: str
    evidence: Optional[str] = None
    severity: RiskLevel = RiskLevel.LOW


class SubstitutionRequest(BaseModel):
    patient_id: int
    prescription_id: int
    prescription_medication_id: int
    original_medicine: str
    requested_alternative: Optional[str] = None


class DecisionResult(BaseModel):
    decision_status: DecisionStatus
    original_medicine: str
    recommended_medicine: Optional[str] = None
    reason: str
    risk_level: RiskLevel = RiskLevel.LOW
    requires_human_confirmation: bool = True
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Prototype decision confidence score between 0.0 and 1.0",
    )
    checks: List[CheckResult] = Field(default_factory=list)


class PresetLookupResponse(BaseModel):
    patient_id: int
    patient_code: str
    prescription_id: int
    prescription_code: str
    prescription_medication_id: int
    medicine_name: str

