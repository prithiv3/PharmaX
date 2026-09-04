from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.allergy import Allergy
from app.models.patient import Patient


def get_patient_by_id(db: Session, patient_id: int) -> Optional[Patient]:
    """Retrieve a patient entity by ID to confirm patient record existence."""
    return db.query(Patient).filter(Patient.id == patient_id).first()


def get_patient_allergies(db: Session, patient_id: int) -> List[Allergy]:
    """Retrieve all recorded synthetic allergies for a patient in deterministic order."""
    return (
        db.query(Allergy)
        .filter(Allergy.patient_id == patient_id)
        .order_by(Allergy.allergen.asc(), Allergy.id.asc())
        .all()
    )
