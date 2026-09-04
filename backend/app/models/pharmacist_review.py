from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class PharmacistReview(Base):
    __tablename__ = "pharmacist_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    decision_id: Mapped[int] = mapped_column(
        ForeignKey("substitution_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    pharmacist_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    decision: Mapped["SubstitutionDecision"] = relationship(
        "SubstitutionDecision", back_populates="pharmacist_reviews"
    )
