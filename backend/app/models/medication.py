from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class PrescriptionMedication(Base):
    __tablename__ = "prescription_medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prescription_id: Mapped[int] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medicine_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    active_ingredient: Mapped[str] = mapped_column(String(255), nullable=False)
    strength: Mapped[str] = mapped_column(String(100), nullable=False)
    dosage_form: Mapped[str] = mapped_column(String(100), nullable=False)
    dose: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    frequency: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    route: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    prescription: Mapped["Prescription"] = relationship(
        "Prescription", back_populates="medications"
    )
    substitution_decisions: Mapped[List["SubstitutionDecision"]] = (
        relationship(
            "SubstitutionDecision",
            back_populates="prescription_medication",
            cascade="all, delete-orphan",
        )
    )
