from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ClinicalConstraint(Base):
    __tablename__ = "clinical_constraints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medicine_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    constraint_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    constraint_rule: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
