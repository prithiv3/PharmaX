from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    sex: Mapped[str] = mapped_column(String(20), nullable=False)
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    pregnancy_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    renal_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    hepatic_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    allergies: Mapped[List["Allergy"]] = relationship(
        "Allergy", back_populates="patient", cascade="all, delete-orphan"
    )
    prescriptions: Mapped[List["Prescription"]] = relationship(
        "Prescription", back_populates="patient", cascade="all, delete-orphan"
    )
    substitution_decisions: Mapped[List["SubstitutionDecision"]] = (
        relationship(
            "SubstitutionDecision",
            back_populates="patient",
            cascade="all, delete-orphan",
        )
    )
