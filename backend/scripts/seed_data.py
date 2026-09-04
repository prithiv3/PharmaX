import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Ensure backend app is in python path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.session import SessionLocal
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


def seed_synthetic_data(reset: bool = False) -> dict:
    """Idempotently seed synthetic domain data for the decision support system.

    If reset=True, clears all existing synthetic tables before seeding.
    """
    db = SessionLocal()
    counts = {
        "patients": 0,
        "allergies": 0,
        "prescriptions": 0,
        "prescription_medications": 0,
        "medicine_alternatives": 0,
        "clinical_constraints": 0,
        "medicine_stock": 0,
    }

    try:
        if reset:
            db.query(AuditLog).delete()
            db.query(PharmacistReview).delete()
            db.query(SubstitutionDecision).delete()
            db.query(MedicineStock).delete()
            db.query(ClinicalConstraint).delete()
            db.query(MedicineAlternative).delete()
            db.query(PrescriptionMedication).delete()
            db.query(Prescription).delete()
            db.query(Allergy).delete()
            db.query(Patient).delete()
            db.commit()

        # 1. Seed Patients (20 synthetic profiles)
        patient_records = [
            {"patient_code": "PAT-0001", "age": 45, "sex": "Female", "weight_kg": Decimal("65.00"), "pregnancy_status": "NOT_PREGNANT", "renal_status": "NORMAL", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0002", "age": 62, "sex": "Male", "weight_kg": Decimal("78.50"), "pregnancy_status": "NOT_APPLICABLE", "renal_status": "SEVERE", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0003", "age": 28, "sex": "Female", "weight_kg": Decimal("58.00"), "pregnancy_status": "PREGNANT", "renal_status": "NORMAL", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0004", "age": 74, "sex": "Male", "weight_kg": Decimal("82.00"), "pregnancy_status": "NOT_APPLICABLE", "renal_status": "MODERATE", "hepatic_status": "MILD"},
            {"patient_code": "PAT-0005", "age": 35, "sex": "Female", "weight_kg": Decimal("70.00"), "pregnancy_status": "NOT_PREGNANT", "renal_status": "NORMAL", "hepatic_status": "MODERATE"},
            {"patient_code": "PAT-0006", "age": 52, "sex": "Male", "weight_kg": Decimal("88.00"), "pregnancy_status": "NOT_APPLICABLE", "renal_status": "NORMAL", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0007", "age": 81, "sex": "Female", "weight_kg": Decimal("54.00"), "pregnancy_status": "NOT_PREGNANT", "renal_status": "SEVERE", "hepatic_status": "MODERATE"},
            {"patient_code": "PAT-0008", "age": 31, "sex": "Female", "weight_kg": Decimal("62.00"), "pregnancy_status": "PREGNANT", "renal_status": "NORMAL", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0009", "age": 40, "sex": "Male", "weight_kg": Decimal("75.00"), "pregnancy_status": "NOT_APPLICABLE", "renal_status": "MILD", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0010", "age": 67, "sex": "Female", "weight_kg": Decimal("69.00"), "pregnancy_status": "NOT_PREGNANT", "renal_status": "NORMAL", "hepatic_status": "SEVERE"},
            {"patient_code": "PAT-0011", "age": 22, "sex": "Male", "weight_kg": Decimal("71.00"), "pregnancy_status": "NOT_APPLICABLE", "renal_status": "NORMAL", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0012", "age": 58, "sex": "Female", "weight_kg": Decimal("80.00"), "pregnancy_status": "NOT_PREGNANT", "renal_status": "MODERATE", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0013", "age": 49, "sex": "Male", "weight_kg": Decimal("92.00"), "pregnancy_status": "NOT_APPLICABLE", "renal_status": "NORMAL", "hepatic_status": "MILD"},
            {"patient_code": "PAT-0014", "age": 30, "sex": "Female", "weight_kg": Decimal("56.00"), "pregnancy_status": "PREGNANT", "renal_status": "NORMAL", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0015", "age": 77, "sex": "Male", "weight_kg": Decimal("68.00"), "pregnancy_status": "NOT_APPLICABLE", "renal_status": "SEVERE", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0016", "age": 19, "sex": "Female", "weight_kg": Decimal("52.00"), "pregnancy_status": "NOT_PREGNANT", "renal_status": "NORMAL", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0017", "age": 64, "sex": "Male", "weight_kg": Decimal("85.00"), "pregnancy_status": "NOT_APPLICABLE", "renal_status": "MILD", "hepatic_status": "MODERATE"},
            {"patient_code": "PAT-0018", "age": 43, "sex": "Female", "weight_kg": Decimal("73.00"), "pregnancy_status": "NOT_PREGNANT", "renal_status": "NORMAL", "hepatic_status": "NORMAL"},
            {"patient_code": "PAT-0019", "age": 86, "sex": "Male", "weight_kg": Decimal("61.00"), "pregnancy_status": "NOT_APPLICABLE", "renal_status": "SEVERE", "hepatic_status": "SEVERE"},
            {"patient_code": "PAT-0020", "age": 37, "sex": "Female", "weight_kg": Decimal("66.00"), "pregnancy_status": "PREGNANT", "renal_status": "NORMAL", "hepatic_status": "NORMAL"},
        ]

        patient_map = {}
        for p_data in patient_records:
            existing = db.query(Patient).filter_by(patient_code=p_data["patient_code"]).first()
            if not existing:
                patient = Patient(**p_data)
                db.add(patient)
                db.flush()
                patient_map[p_data["patient_code"]] = patient
                counts["patients"] += 1
            else:
                for k, v in p_data.items():
                    setattr(existing, k, v)
                patient_map[p_data["patient_code"]] = existing

        # 2. Seed Allergies
        allergy_records = [
            {"patient_code": "PAT-0002", "allergen": "PENICILLIN", "reaction": "HIVES", "severity": "SEVERE"},
            {"patient_code": "PAT-0002", "allergen": "SULFONAMIDE", "reaction": "BREATHING_DIFFICULTY", "severity": "SEVERE"},
            {"patient_code": "PAT-0004", "allergen": "NSAID", "reaction": "HIVES", "severity": "MODERATE"},
            {"patient_code": "PAT-0007", "allergen": "MACROLIDE", "reaction": "RASH", "severity": "SEVERE"},
            {"patient_code": "PAT-0010", "allergen": "PENICILLIN", "reaction": "BREATHING_DIFFICULTY", "severity": "SEVERE"},
            {"patient_code": "PAT-0012", "allergen": "SULFONAMIDE", "reaction": "RASH", "severity": "MODERATE"},
            {"patient_code": "PAT-0015", "allergen": "NSAID", "reaction": "BREATHING_DIFFICULTY", "severity": "SEVERE"},
            {"patient_code": "PAT-0017", "allergen": "MACROLIDE", "reaction": "HIVES", "severity": "MODERATE"},
            {"patient_code": "PAT-0018", "allergen": "CODEINE", "reaction": "NAUSEA", "severity": "MILD"},
        ]

        for a_data in allergy_records:
            p_code = a_data["patient_code"]
            patient = patient_map[p_code]
            existing = db.query(Allergy).filter_by(patient_id=patient.id, allergen=a_data["allergen"]).first()
            if not existing:
                allergy = Allergy(
                    patient_id=patient.id,
                    allergen=a_data["allergen"],
                    reaction=a_data["reaction"],
                    severity=a_data["severity"],
                )
                db.add(allergy)
                counts["allergies"] += 1

        # 3. Seed Prescriptions (30 RXs with deterministic patient and medication mappings)
        rx_specifications = [
            # RX-0001 .. RX-0020 (Primary prescription for PAT-0001 .. PAT-0020)
            ("RX-0001", "PAT-0001", "Lisinopril 10mg Tablet", "Lisinopril", "10mg", "Tablet", "1 tablet", "QD", 30, "Oral"),
            ("RX-0002", "PAT-0002", "Amoxicillin 500mg Capsule", "Amoxicillin", "500mg", "Capsule", "1 capsule", "TID", 7, "Oral"),
            ("RX-0003", "PAT-0003", "Losartan 50mg Tablet", "Losartan", "50mg", "Tablet", "1 tablet", "QD", 30, "Oral"),
            ("RX-0004", "PAT-0004", "Ibuprofen 400mg Tablet", "Ibuprofen", "400mg", "Tablet", "1 tablet", "Q8H", 5, "Oral"),
            ("RX-0005", "PAT-0005", "Metformin 500mg Tablet", "Metformin", "500mg", "Tablet", "1 tablet", "BID", 30, "Oral"),
            ("RX-0006", "PAT-0006", "Omeprazole 20mg Capsule", "Omeprazole", "20mg", "Capsule", "1 capsule", "QD", 14, "Oral"),
            ("RX-0007", "PAT-0007", "Clarithromycin 500mg Tablet", "Clarithromycin", "500mg", "Tablet", "1 tablet", "BID", 7, "Oral"),
            ("RX-0008", "PAT-0008", "Naproxen 500mg Tablet", "Naproxen", "500mg", "Tablet", "1 tablet", "BID", 7, "Oral"),
            ("RX-0009", "PAT-0009", "Cefalexin 500mg Capsule", "Cefalexin", "500mg", "Capsule", "1 capsule", "QID", 7, "Oral"),
            ("RX-0010", "PAT-0010", "Ciprofloxacin 500mg Tablet", "Ciprofloxacin", "500mg", "Tablet", "1 tablet", "BID", 7, "Oral"),
            ("RX-0011", "PAT-0011", "Doxycycline 100mg Capsule", "Doxycycline", "100mg", "Capsule", "1 capsule", "BID", 7, "Oral"),
            ("RX-0012", "PAT-0012", "Atorvastatin 20mg Tablet", "Atorvastatin", "20mg", "Tablet", "1 tablet", "QD", 30, "Oral"),
            ("RX-0013", "PAT-0013", "Amlodipine 5mg Tablet", "Amlodipine", "5mg", "Tablet", "1 tablet", "QD", 30, "Oral"),
            ("RX-0014", "PAT-0014", "Hydrochlorothiazide 25mg Tablet", "Hydrochlorothiazide", "25mg", "Tablet", "1 tablet", "QD", 30, "Oral"),
            ("RX-0015", "PAT-0015", "Azithromycin 250mg Tablet", "Azithromycin", "250mg", "Tablet", "2 tablets day 1, 1 daily", "QD", 5, "Oral"),
            ("RX-0016", "PAT-0016", "Amoxicillin 500mg Capsule", "Amoxicillin", "500mg", "Capsule", "1 capsule", "TID", 7, "Oral"),
            ("RX-0017", "PAT-0017", "Ibuprofen 400mg Tablet", "Ibuprofen", "400mg", "Tablet", "1 tablet", "Q8H", 5, "Oral"),
            ("RX-0018", "PAT-0018", "Lisinopril 10mg Tablet", "Lisinopril", "10mg", "Tablet", "1 tablet", "QD", 30, "Oral"),
            ("RX-0019", "PAT-0019", "Metformin 500mg Tablet", "Metformin", "500mg", "Tablet", "1 tablet", "BID", 30, "Oral"),
            ("RX-0020", "PAT-0020", "Losartan 50mg Tablet", "Losartan", "50mg", "Tablet", "1 tablet", "QD", 30, "Oral"),

            # RX-0021 .. RX-0030 (Secondary prescriptions for PAT-0001 .. PAT-0010)
            ("RX-0021", "PAT-0001", "Omeprazole 20mg Capsule", "Omeprazole", "20mg", "Capsule", "1 capsule", "QD", 14, "Oral"),
            ("RX-0022", "PAT-0002", "Azithromycin 250mg Tablet", "Azithromycin", "250mg", "Tablet", "2 tablets day 1, 1 daily", "QD", 5, "Oral"),
            ("RX-0023", "PAT-0003", "Ibuprofen 400mg Tablet", "Ibuprofen", "400mg", "Tablet", "1 tablet", "Q8H", 5, "Oral"),
            ("RX-0024", "PAT-0004", "Metformin 500mg Tablet", "Metformin", "500mg", "Tablet", "1 tablet", "BID", 30, "Oral"),
            ("RX-0025", "PAT-0005", "Lisinopril 10mg Tablet", "Lisinopril", "10mg", "Tablet", "1 tablet", "QD", 30, "Oral"),
            ("RX-0026", "PAT-0006", "Losartan 50mg Tablet", "Losartan", "50mg", "Tablet", "1 tablet", "QD", 30, "Oral"),
            ("RX-0027", "PAT-0007", "Clarithromycin 500mg Tablet", "Clarithromycin", "500mg", "Tablet", "1 tablet", "BID", 7, "Oral"),
            ("RX-0028", "PAT-0008", "Naproxen 500mg Tablet", "Naproxen", "500mg", "Tablet", "1 tablet", "BID", 7, "Oral"),
            ("RX-0029", "PAT-0009", "Cefalexin 500mg Capsule", "Cefalexin", "500mg", "Capsule", "1 capsule", "QID", 7, "Oral"),
            ("RX-0030", "PAT-0010", "Ciprofloxacin 500mg Tablet", "Ciprofloxacin", "500mg", "Tablet", "1 tablet", "BID", 7, "Oral"),
        ]

        for rx_code, p_code, med_name, ing, str_val, form, dose, freq, dur, route in rx_specifications:
            patient = patient_map[p_code]
            existing_rx = db.query(Prescription).filter_by(prescription_code=rx_code).first()
            if not existing_rx:
                rx = Prescription(
                    patient_id=patient.id,
                    prescription_code=rx_code,
                    prescriber_rule_code="RULE-ALLOW-GENERIC",
                    status="active",
                )
                db.add(rx)
                db.flush()
                counts["prescriptions"] += 1
            else:
                rx = existing_rx
                rx.patient_id = patient.id

            existing_med = db.query(PrescriptionMedication).filter_by(prescription_id=rx.id).first()
            if not existing_med:
                med = PrescriptionMedication(
                    prescription_id=rx.id,
                    medicine_name=med_name,
                    active_ingredient=ing,
                    strength=str_val,
                    dosage_form=form,
                    dose=dose,
                    frequency=freq,
                    duration_days=dur,
                    route=route,
                )
                db.add(med)
                counts["prescription_medications"] += 1
            else:
                existing_med.medicine_name = med_name
                existing_med.active_ingredient = ing
                existing_med.strength = str_val
                existing_med.dosage_form = form
                existing_med.dose = dose
                existing_med.frequency = freq
                existing_med.duration_days = dur
                existing_med.route = route

        # 4. Seed Medicine Alternatives (18 curated prototype rules)
        disclaimer_text = "Synthetic prototype rule for software testing only."
        alt_records = [
            ("Amoxicillin 500mg Capsule", "Cefalexin 500mg Capsule", "Amoxicillin", "Cefalexin", "Therapeutic Equivalent"),
            ("Amoxicillin 500mg Capsule", "Ampicillin 500mg Capsule", "Amoxicillin", "Ampicillin", "Chemical Equivalent"),
            ("Azithromycin 250mg Tablet", "Clarithromycin 250mg Tablet", "Azithromycin", "Clarithromycin", "Therapeutic Equivalent"),
            ("Azithromycin 250mg Tablet", "Erythromycin 250mg Tablet", "Azithromycin", "Erythromycin", "Therapeutic Equivalent"),
            ("Ibuprofen 400mg Tablet", "Naproxen 250mg Tablet", "Ibuprofen", "Naproxen", "Therapeutic Equivalent"),
            ("Ibuprofen 400mg Tablet", "Celecoxib 100mg Capsule", "Ibuprofen", "Celecoxib", "Therapeutic Equivalent"),
            ("Lisinopril 10mg Tablet", "Enalapril 10mg Tablet", "Lisinopril", "Enalapril", "Chemical Equivalent"),
            ("Lisinopril 10mg Tablet", "Losartan 50mg Tablet", "Lisinopril", "Losartan", "Therapeutic Class Equivalent"),
            ("Losartan 50mg Tablet", "Valsartan 80mg Tablet", "Losartan", "Valsartan", "Chemical Class Equivalent"),
            ("Metformin 500mg Tablet", "Gliclazide 80mg Tablet", "Metformin", "Gliclazide", "Therapeutic Alternative"),
            ("Omeprazole 20mg Capsule", "Esomeprazole 20mg Capsule", "Omeprazole", "Esomeprazole", "Chemical Equivalent"),
            ("Omeprazole 20mg Capsule", "Pantoprazole 40mg Tablet", "Omeprazole", "Pantoprazole", "Therapeutic Equivalent"),
            ("Cefalexin 500mg Capsule", "Cefuroxime 250mg Tablet", "Cefalexin", "Cefuroxime", "Therapeutic Equivalent"),
            ("Ciprofloxacin 500mg Tablet", "Levofloxacin 500mg Tablet", "Ciprofloxacin", "Levofloxacin", "Chemical Class Equivalent"),
            ("Doxycycline 100mg Capsule", "Tetracycline 250mg Capsule", "Doxycycline", "Tetracycline", "Chemical Class Equivalent"),
            ("Atorvastatin 20mg Tablet", "Rosuvastatin 10mg Tablet", "Atorvastatin", "Rosuvastatin", "Therapeutic Equivalent"),
            ("Amlodipine 5mg Tablet", "Nifedipine 20mg Tablet", "Amlodipine", "Nifedipine", "Chemical Class Equivalent"),
            ("Hydrochlorothiazide 25mg Tablet", "Indapamide 2.5mg Tablet", "Hydrochlorothiazide", "Indapamide", "Therapeutic Equivalent"),
        ]

        for src, alt_med, src_ing, alt_ing, eq_type in alt_records:
            existing = db.query(MedicineAlternative).filter_by(source_medicine=src, alternative_medicine=alt_med).first()
            if not existing:
                alt = MedicineAlternative(
                    source_medicine=src,
                    alternative_medicine=alt_med,
                    source_ingredient=src_ing,
                    alternative_ingredient=alt_ing,
                    equivalence_type=eq_type,
                    equivalence_evidence=disclaimer_text,
                    clinical_notes="Demonstration alternative relationship.",
                    is_active=True,
                )
                db.add(alt)
                counts["medicine_alternatives"] += 1

        # 5. Seed Clinical Constraints (20 synthetic constraints)
        constraint_evidence = "Synthetic prototype constraint for testing only."
        constraint_records = [
            ("Cefalexin 500mg Capsule", "ALLERGY", "Cross-reactivity block if patient has PENICILLIN allergy", "CRITICAL"),
            ("Ampicillin 500mg Capsule", "ALLERGY", "Contraindicated if patient has PENICILLIN allergy", "CRITICAL"),
            ("Clarithromycin 250mg Tablet", "ALLERGY", "Contraindicated if patient has MACROLIDE allergy", "CRITICAL"),
            ("Naproxen 250mg Tablet", "ALLERGY", "Contraindicated if patient has NSAID allergy", "CRITICAL"),
            ("Celecoxib 100mg Capsule", "ALLERGY", "Contraindicated if patient has SULFONAMIDE or NSAID allergy", "CRITICAL"),
            ("Ciprofloxacin 500mg Tablet", "RENAL", "Requires dose reduction or block if renal status is SEVERE", "HIGH"),
            ("Metformin 500mg Tablet", "RENAL", "Contraindicated if renal status is SEVERE", "CRITICAL"),
            ("Lisinopril 10mg Tablet", "RENAL", "Requires serum potassium monitoring if renal status is SEVERE", "HIGH"),
            ("Atorvastatin 20mg Tablet", "HEPATIC", "Contraindicated if hepatic status is SEVERE", "CRITICAL"),
            ("Metformin 500mg Tablet", "HEPATIC", "Contraindicated if hepatic status is SEVERE", "CRITICAL"),
            ("Losartan 50mg Tablet", "PREGNANCY", "Contraindicated during PREGNANCY (Teratogenic risk)", "CRITICAL"),
            ("Valsartan 80mg Tablet", "PREGNANCY", "Contraindicated during PREGNANCY (Teratogenic risk)", "CRITICAL"),
            ("Ciprofloxacin 500mg Tablet", "PREGNANCY", "Contraindicated during PREGNANCY", "HIGH"),
            ("Ciprofloxacin 500mg Tablet", "AGE", "Contraindicated in pediatric patients under 18 years old", "HIGH"),
            ("Doxycycline 100mg Capsule", "AGE", "Contraindicated in pediatric patients under 8 years old", "HIGH"),
            ("Clarithromycin 250mg Tablet", "DRUG_INTERACTION", "Severe interaction with Atorvastatin (Rhabdomyolysis risk)", "CRITICAL"),
            ("Lisinopril 10mg Tablet", "DRUG_INTERACTION", "Hyperkalemia risk with Potassium-sparing diuretics", "HIGH"),
            ("Amoxicillin 500mg Capsule", "DOSAGE", "Maximum daily dose limit 3000mg per day", "MODERATE"),
            ("Ibuprofen 400mg Tablet", "DOSAGE", "Maximum daily dose limit 2400mg per day", "MODERATE"),
            ("Paracetamol 500mg Tablet", "DOSAGE", "Maximum daily dose limit 4000mg per day", "MODERATE"),
        ]

        for med, c_type, c_rule, sev in constraint_records:
            existing = db.query(ClinicalConstraint).filter_by(medicine_name=med, constraint_type=c_type).first()
            if not existing:
                c = ClinicalConstraint(
                    medicine_name=med,
                    constraint_type=c_type,
                    constraint_rule=c_rule,
                    severity=sev,
                    evidence_source=constraint_evidence,
                    is_active=True,
                )
                db.add(c)
                counts["clinical_constraints"] += 1

        # 6. Seed Medicine Stock (Scenarios: In-Stock, Zero-Stock, Unavailable)
        stock_records = [
            ("Cefalexin 500mg Capsule", "BATCH-0001", 250, date.today() + timedelta(days=365), "Shelf-A1", True),
            ("Ampicillin 500mg Capsule", "BATCH-0002", 0, date.today() + timedelta(days=180), "Shelf-A2", True),  # Zero stock
            ("Clarithromycin 250mg Tablet", "BATCH-0003", 100, date.today() + timedelta(days=240), "Shelf-B1", False),  # Marked unavailable
            ("Erythromycin 250mg Tablet", "BATCH-0004", 50, date.today() + timedelta(days=300), "Shelf-B2", True),
            ("Naproxen 250mg Tablet", "BATCH-0005", 300, date.today() + timedelta(days=400), "Shelf-C1", True),
            ("Celecoxib 100mg Capsule", "BATCH-0006", 120, date.today() + timedelta(days=365), "Shelf-C2", True),
            ("Enalapril 10mg Tablet", "BATCH-0007", 80, date.today() + timedelta(days=200), "Shelf-D1", True),
            ("Losartan 50mg Tablet", "BATCH-0008", 200, date.today() + timedelta(days=500), "Shelf-D2", True),
            ("Valsartan 80mg Tablet", "BATCH-0009", 90, date.today() + timedelta(days=365), "Shelf-D3", True),
            ("Gliclazide 80mg Tablet", "BATCH-0010", 0, date.today() + timedelta(days=120), "Shelf-E1", True),  # Zero stock
            ("Esomeprazole 20mg Capsule", "BATCH-0011", 150, date.today() + timedelta(days=365), "Shelf-F1", True),
            ("Pantoprazole 40mg Tablet", "BATCH-0012", 180, date.today() + timedelta(days=365), "Shelf-F2", True),
            ("Cefuroxime 250mg Tablet", "BATCH-0013", 75, date.today() + timedelta(days=180), "Shelf-A3", True),
            ("Levofloxacin 500mg Tablet", "BATCH-0014", 60, date.today() + timedelta(days=300), "Shelf-G1", True),
            ("Tetracycline 250mg Capsule", "BATCH-0015", 0, date.today() + timedelta(days=90), "Shelf-G2", False),  # Unavailable & 0 stock
            ("Rosuvastatin 10mg Tablet", "BATCH-0016", 210, date.today() + timedelta(days=450), "Shelf-H1", True),
            ("Nifedipine 20mg Tablet", "BATCH-0017", 110, date.today() + timedelta(days=365), "Shelf-I1", True),
            ("Indapamide 2.5mg Tablet", "BATCH-0018", 95, date.today() + timedelta(days=365), "Shelf-J1", True),
        ]

        for med, b_code, qty, exp, loc, avail in stock_records:
            existing = db.query(MedicineStock).filter_by(batch_code=b_code).first()
            if not existing:
                s = MedicineStock(
                    medicine_name=med,
                    batch_code=b_code,
                    quantity_available=qty,
                    expiry_date=exp,
                    pharmacy_location=loc,
                    is_available=avail,
                )
                db.add(s)
                counts["medicine_stock"] += 1
            else:
                existing.medicine_name = med
                existing.quantity_available = qty
                existing.expiry_date = exp
                existing.pharmacy_location = loc
                existing.is_available = avail

        db.commit()
        return counts

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_db = "--reset" in sys.argv
    print(f"Seeding synthetic data into PostgreSQL (reset={reset_db})...")
    res = seed_synthetic_data(reset=reset_db)
    print("Seeding completed successfully.")
    print("New Records Inserted:")
    for k, v in res.items():
        print(f"  - {k}: {v}")
