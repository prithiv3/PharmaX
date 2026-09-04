from typing import List
from sqlalchemy.orm import Session
from app.models.medication import PrescriptionMedication
from app.models.prescription import Prescription


def get_patient_prescribed_medications(
    db: Session, patient_id: int
) -> List[PrescriptionMedication]:
    """Retrieve all active prescription medications for a patient in deterministic order."""
    return (
        db.query(PrescriptionMedication)
        .join(Prescription, PrescriptionMedication.prescription_id == Prescription.id)
        .filter(
            Prescription.patient_id == patient_id,
            Prescription.status == "active",
        )
        .order_by(PrescriptionMedication.medicine_name.asc(), PrescriptionMedication.id.asc())
        .all()
    )
