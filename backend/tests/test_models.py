from decimal import Decimal
import pytest
from sqlalchemy import inspect
from app.db.session import SessionLocal, check_db_connection, engine
from app.models import (
    Allergy,
    AuditLog,
    ClinicalConstraint,
    MedicineAlternative,
    MedicineStock,
    Patient,
    PharmacistReview,
    Prescription,
    PrescriptionMedication,
    SubstitutionDecision,
)


def test_db_connection():
    """Verify that PostgreSQL database connection is healthy."""
    assert check_db_connection() is True


def test_all_tables_exist():
    """Verify that all 10 expected domain tables exist in PostgreSQL after Alembic migration."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = {
        "patients",
        "allergies",
        "prescriptions",
        "prescription_medications",
        "medicine_alternatives",
        "clinical_constraints",
        "medicine_stock",
        "substitution_decisions",
        "pharmacist_reviews",
        "audit_logs",
    }
    assert expected_tables.issubset(existing_tables)


def test_synthetic_data_lifecycle_and_relationships():
    """Verify CRUD and relationship navigation across all domain entities using synthetic test data with full cleanup."""
    db = SessionLocal()
    try:
        # 1. Insert synthetic patient
        patient = Patient(
            patient_code="SYNTH-PAT-0001",
            age=45,
            sex="Female",
            weight_kg=Decimal("68.50"),
            pregnancy_status="No",
            renal_status="Normal",
            hepatic_status="Normal",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        assert patient.id is not None
        assert patient.patient_code == "SYNTH-PAT-0001"

        # 2. Add allergy to patient
        allergy = Allergy(
            patient_id=patient.id,
            allergen="Penicillin",
            reaction="Hives / Rash",
            severity="Moderate",
        )
        db.add(allergy)
        db.commit()
        db.refresh(allergy)
        assert allergy.id is not None
        assert allergy.patient.patient_code == "SYNTH-PAT-0001"

        # 3. Add prescription to patient
        prescription = Prescription(
            patient_id=patient.id,
            prescription_code="SYNTH-RX-9001",
            prescriber_rule_code="RULE-ALLOW-GENERIC",
            status="active",
        )
        db.add(prescription)
        db.commit()
        db.refresh(prescription)
        assert prescription.id is not None
        assert prescription.patient.patient_code == "SYNTH-PAT-0001"

        # 4. Add medication to prescription
        medication = PrescriptionMedication(
            prescription_id=prescription.id,
            medicine_name="Amoxicillin 500mg Capsule",
            active_ingredient="Amoxicillin",
            strength="500mg",
            dosage_form="Capsule",
            dose="1 capsule",
            frequency="TID",
            duration_days=7,
            route="Oral",
        )
        db.add(medication)
        db.commit()
        db.refresh(medication)
        assert medication.id is not None
        assert medication.prescription.prescription_code == "SYNTH-RX-9001"

        # 5. Add substitution decision referencing patient & medication
        decision = SubstitutionDecision(
            patient_id=patient.id,
            prescription_medication_id=medication.id,
            original_medicine="Amoxicillin 500mg Capsule",
            recommended_medicine="Cefalexin 500mg Capsule",
            decision_status="BLOCKED",
            reason="Synthetic penicillin allergy constraint triggered",
            rule_evidence="Allergy record matched Penicillin group",
            risk_level="High",
            requires_human_confirmation=True,
            confidence_score=Decimal("0.9500"),
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)
        assert decision.id is not None
        assert decision.patient.patient_code == "SYNTH-PAT-0001"
        assert decision.prescription_medication.medicine_name == "Amoxicillin 500mg Capsule"

        # 6. Add pharmacist review referencing decision
        review = PharmacistReview(
            decision_id=decision.id,
            review_status="REJECTED",
            pharmacist_code="PHARM-8821",
            override_reason="Confirmed patient penicillin allergy",
            review_notes="Maintained substitution block.",
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        assert review.id is not None
        assert review.decision.id == decision.id

        # 7. Add audit log referencing decision
        audit = AuditLog(
            decision_id=decision.id,
            action="SUBSTITUTION_REJECTED",
            previous_status="BLOCKED",
            new_status="REJECTED",
            reason="Pharmacist confirmed substitution block due to allergy",
            actor_code="PHARM-8821",
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        assert audit.id is not None
        assert audit.decision.id == decision.id

        # Verify relationship collections navigation
        assert len(patient.allergies) == 1
        assert len(patient.prescriptions) == 1
        assert len(prescription.medications) == 1
        assert len(patient.substitution_decisions) == 1
        assert len(decision.pharmacist_reviews) == 1
        assert len(decision.audit_logs) == 1

    finally:
        # Test Data Cleanup (Cascade deletion removes linked entities)
        db.rollback()
        patient_obj = db.query(Patient).filter_by(patient_code="SYNTH-PAT-0001").first()
        if patient_obj:
            db.delete(patient_obj)
            db.commit()
        db.close()


def test_independent_synthetic_models():
    """Verify insertion and querying for standalone synthetic entities (alternatives, clinical constraints, stock)."""
    db = SessionLocal()
    try:
        # MedicineAlternative
        alt = MedicineAlternative(
            source_medicine="SynthMed Alpha 100mg",
            alternative_medicine="SynthMed Beta 100mg",
            source_ingredient="SynthIngred Alpha",
            alternative_ingredient="SynthIngred Alpha",
            equivalence_type="Therapeutic Equivalent",
            equivalence_evidence="Synthetic prototype equivalence table",
            clinical_notes="Demonstration alternative relationship only",
            is_active=True,
        )
        # ClinicalConstraint
        constraint = ClinicalConstraint(
            medicine_name="SynthMed Alpha 100mg",
            constraint_type="ALLERGY",
            constraint_rule="Block if patient has synthetic Penicillin allergy",
            severity="CRITICAL",
            evidence_source="Synthetic prototype clinical guidelines",
            is_active=True,
        )
        # MedicineStock
        stock = MedicineStock(
            medicine_name="SynthMed Beta 100mg",
            batch_code="BATCH-2026-001",
            quantity_available=150,
            pharmacy_location="Shelf-A3",
            is_available=True,
        )

        db.add_all([alt, constraint, stock])
        db.commit()

        assert alt.id is not None
        assert constraint.id is not None
        assert stock.id is not None

        # Clean up
        db.delete(alt)
        db.delete(constraint)
        db.delete(stock)
        db.commit()
    finally:
        db.close()
