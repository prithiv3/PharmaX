from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MedicineStock(Base):
    __tablename__ = "medicine_stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medicine_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    batch_code: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_available: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    pharmacy_location: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
