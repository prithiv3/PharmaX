from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class SubstitutionDecision(Base):
    __tablename__ = "substitution_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prescription_medication_id: Mapped[int] = mapped_column(
        ForeignKey("prescription_medications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_medicine: Mapped[str] = mapped_column(String(255), nullable=False)
    recommended_medicine: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    decision_status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rule_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    requires_human_confirmation: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient", back_populates="substitution_decisions"
    )
    prescription_medication: Mapped["PrescriptionMedication"] = relationship(
        "PrescriptionMedication", back_populates="substitution_decisions"
    )
    pharmacist_reviews: Mapped[List["PharmacistReview"]] = relationship(
        "PharmacistReview",
        back_populates="decision",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="decision",
        cascade="all, delete-orphan",
    )
