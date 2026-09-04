from datetime import datetime
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prescription_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    prescriber_rule_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient", back_populates="prescriptions"
    )
    medications: Mapped[List["PrescriptionMedication"]] = relationship(
        "PrescriptionMedication",
        back_populates="prescription",
        cascade="all, delete-orphan",
    )
