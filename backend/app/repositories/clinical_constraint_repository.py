from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.clinical_constraint import ClinicalConstraint


def get_active_clinical_constraints(
    db: Session, medicine_name: str, constraint_type: Optional[str] = None
) -> List[ClinicalConstraint]:
    """Retrieve active clinical constraints for a medicine in deterministic order.

    Uses exact normalized case matching (lower/trim) without fuzzy or substring matching.
    """
    if not medicine_name or not medicine_name.strip():
        return []

    norm_medicine = medicine_name.strip().lower()

    query = db.query(ClinicalConstraint).filter(
        ClinicalConstraint.is_active.is_(True),
        func.lower(func.trim(ClinicalConstraint.medicine_name)) == norm_medicine,
    )

    if constraint_type and constraint_type.strip():
        norm_type = constraint_type.strip().lower()
        query = query.filter(
            func.lower(func.trim(ClinicalConstraint.constraint_type)) == norm_type
        )

    return query.order_by(
        ClinicalConstraint.constraint_type.asc(), ClinicalConstraint.id.asc()
    ).all()


def get_active_drug_interaction_constraints(
    db: Session, medicine_name: str
) -> List[ClinicalConstraint]:
    """Retrieve active DRUG_INTERACTION clinical constraints for a medicine in deterministic order."""
    return get_active_clinical_constraints(
        db, medicine_name=medicine_name, constraint_type="DRUG_INTERACTION"
    )


def get_active_dosage_constraints(
    db: Session, medicine_name: str
) -> List[ClinicalConstraint]:
    """Retrieve active DOSAGE clinical constraints for a medicine in deterministic order."""
    return get_active_clinical_constraints(
        db, medicine_name=medicine_name, constraint_type="DOSAGE"
    )
