from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MedicineAlternative(Base):
    __tablename__ = "medicine_alternatives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_medicine: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    alternative_medicine: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    source_ingredient: Mapped[str] = mapped_column(String(255), nullable=False)
    alternative_ingredient: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    equivalence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    equivalence_evidence: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    clinical_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
