from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.alternative import MedicineAlternative


def get_active_alternatives_for_medicine(
    db: Session, source_medicine: str
) -> List[MedicineAlternative]:
    """Retrieve all active, approved candidate alternatives for a source medicine.

    Uses exact normalized case matching (lower/trim) without fuzzy or substring matching.
    Returns results in deterministic order.
    """
    if not source_medicine or not source_medicine.strip():
        return []

    normalized_source = source_medicine.strip().lower()

    return (
        db.query(MedicineAlternative)
        .filter(
            MedicineAlternative.is_active.is_(True),
            func.lower(func.trim(MedicineAlternative.source_medicine))
            == normalized_source,
        )
        .order_by(
            MedicineAlternative.alternative_medicine.asc(),
            MedicineAlternative.id.asc(),
        )
        .all()
    )
