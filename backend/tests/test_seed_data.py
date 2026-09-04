from app.db.session import SessionLocal
from app.models import (
    Allergy,
    ClinicalConstraint,
    MedicineAlternative,
    MedicineStock,
    Patient,
    Prescription,
    PrescriptionMedication,
)
from scripts.seed_data import seed_synthetic_data


def test_seed_execution_and_idempotency():
    """Verify that seed_synthetic_data executes cleanly and is idempotent."""
    res = seed_synthetic_data()
    # On a database that is already seeded, new insertions should be 0
    assert res["patients"] == 0
    assert res["allergies"] == 0
    assert res["prescriptions"] == 0
    assert res["prescription_medications"] == 0
    assert res["medicine_alternatives"] == 0
    assert res["clinical_constraints"] == 0
    assert res["medicine_stock"] == 0


def test_seeded_data_counts_and_foreign_keys():
    """Verify record counts and foreign key integrity across all seeded synthetic domain tables."""
    db = SessionLocal()
    try:
        # Check record counts
        patients_count = db.query(Patient).count()
        allergies_count = db.query(Allergy).count()
        prescriptions_count = db.query(Prescription).count()
        meds_count = db.query(PrescriptionMedication).count()
        alts_count = db.query(MedicineAlternative).count()
        constraints_count = db.query(ClinicalConstraint).count()
        stock_count = db.query(MedicineStock).count()

        assert patients_count >= 20
        assert allergies_count >= 9
        assert prescriptions_count >= 30
        assert meds_count >= 30
        assert alts_count >= 18
        assert constraints_count >= 20
        assert stock_count >= 18

        # Check FK integrity for Patients -> Allergies
        sample_allergy = db.query(Allergy).first()
        assert sample_allergy is not None
        assert sample_allergy.patient is not None
        assert sample_allergy.patient.patient_code.startswith("PAT-")

        # Check FK integrity for Patients -> Prescriptions -> Medications
        sample_med = db.query(PrescriptionMedication).first()
        assert sample_med is not None
        assert sample_med.prescription is not None
        assert sample_med.prescription.patient is not None
        assert sample_med.prescription.prescription_code.startswith("RX-")

    finally:
        db.close()
