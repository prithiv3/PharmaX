from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.stock import MedicineStock


def get_available_stock_for_medicine(
    db: Session, medicine_name: str
) -> List[MedicineStock]:
    """Retrieve active stock records with quantity_available > 0 for a medicine in deterministic order.

    Uses exact normalized case matching without fuzzy or substring matching.
    """
    if not medicine_name or not medicine_name.strip():
        return []

    norm_medicine = medicine_name.strip().lower()

    return (
        db.query(MedicineStock)
        .filter(
            MedicineStock.is_available.is_(True),
            MedicineStock.quantity_available > 0,
            func.lower(func.trim(MedicineStock.medicine_name)) == norm_medicine,
        )
        .order_by(
            MedicineStock.expiry_date.asc(),
            MedicineStock.batch_code.asc(),
            MedicineStock.id.asc(),
        )
        .all()
    )


def get_stock_records_for_medicine(
    db: Session, medicine_name: str
) -> List[MedicineStock]:
    """Retrieve all stock records for a medicine in deterministic order."""
    if not medicine_name or not medicine_name.strip():
        return []

    norm_medicine = medicine_name.strip().lower()

    return (
        db.query(MedicineStock)
        .filter(
            func.lower(func.trim(MedicineStock.medicine_name)) == norm_medicine,
        )
        .order_by(
            MedicineStock.expiry_date.asc(),
            MedicineStock.batch_code.asc(),
            MedicineStock.id.asc(),
        )
        .all()
    )
