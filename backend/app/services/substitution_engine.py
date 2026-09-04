"""Pharmacy Substitution Decision Support Engine - Module with Approved Alternative Lookup, Allergy, Renal, Hepatic, Pregnancy, Age, Drug Interaction, Dosage, & Stock Safety Checks.

Note: The confidence_score field is a prototype decision-support heuristic
metric and NOT a clinical or medical probability calculation.
"""

from datetime import date
import re
from typing import List, Optional
from app.models.allergy import Allergy
from app.models.alternative import MedicineAlternative
from app.models.clinical_constraint import ClinicalConstraint
from app.models.medication import PrescriptionMedication
from app.models.patient import Patient
from app.models.stock import MedicineStock
from app.schemas.substitution import (
    CheckResult,
    CheckStatus,
    DecisionResult,
    DecisionStatus,
    RiskLevel,
    SubstitutionRequest,
)

# Synthetic cross-reactivity & group mapping dictionary for software prototype testing
ALLERGEN_GROUP_MAPPING = {
    "penicillin": {"penicillin", "amoxicillin", "ampicillin", "cefalexin", "cefaclor", "cefuroxime"},
    "sulfonamide": {"sulfonamide", "sulfamethoxazole", "celecoxib", "gliclazide", "indapamide"},
    "nsaid": {"nsaid", "ibuprofen", "naproxen", "celecoxib", "aspirin", "diclofenac"},
    "macrolide": {"macrolide", "azithromycin", "clarithromycin", "erythromycin"},
}


def _map_severity(severity_str: Optional[str]) -> RiskLevel:
    """Map string severity to RiskLevel enum."""
    sev = (severity_str or "").strip().upper()
    if sev in ("CRITICAL", "SEVERE"):
        return RiskLevel.CRITICAL
    elif sev in ("HIGH", "MODERATE"):
        return RiskLevel.HIGH
    elif sev == "MILD":
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def _parse_daily_frequency_count(freq_str: str) -> float:
    """Parse frequency string into daily multiplier count."""
    f = freq_str.strip().lower()
    if any(k in f for k in ["qid", "four times", "4 times", "4x"]):
        return 4.0
    elif any(k in f for k in ["tid", "three times", "3 times", "3x"]):
        return 3.0
    elif any(k in f for k in ["bid", "twice", "2 times", "2x"]):
        return 2.0
    elif any(k in f for k in ["daily", "once daily", "qd", "every day", "1x"]):
        return 1.0
    elif "weekly" in f or "once weekly" in f:
        return 1.0 / 7.0
    return 1.0


def _parse_mg_value(val_str: str) -> float:
    """Extract numeric mg dose from dose or strength string."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mg)?", val_str.strip().lower())
    if match:
        return float(match.group(1))
    return 0.0


def evaluate_approved_alternative_check(
    original_medicine: str, candidates: List[MedicineAlternative]
) -> CheckResult:
    """Pure rule check for approved alternative lookup in candidate catalog."""
    if not candidates:
        return CheckResult(
            check_name="approved_alternative",
            status=CheckStatus.FAIL,
            reason="No active approved alternative was found for the requested medicine.",
            evidence="Synthetic prototype dataset query returned 0 active matching alternatives.",
            severity=RiskLevel.LOW,
        )

    alt_names = ", ".join([c.alternative_medicine for c in candidates])
    return CheckResult(
        check_name="approved_alternative",
        status=CheckStatus.PASS,
        reason=f"Found {len(candidates)} active approved candidate alternative(s) in prototype dataset: {alt_names}",
        evidence=f"Matched {len(candidates)} curated alternative entry/entries.",
        severity=RiskLevel.LOW,
    )


def evaluate_patient_allergy_check(
    patient_exists: bool,
    allergies: List[Allergy],
    alternative_medicine: str,
    alternative_ingredient: str,
) -> CheckResult:
    """Pure rule check evaluating candidate alternative against patient's synthetic allergy records."""
    if not patient_exists:
        return CheckResult(
            check_name="allergy",
            status=CheckStatus.FAIL,
            reason="Patient record ID not found in prototype database.",
            evidence="Patient lookup returned None.",
            severity=RiskLevel.HIGH,
        )

    if not allergies:
        return CheckResult(
            check_name="allergy",
            status=CheckStatus.PASS,
            reason="No recorded allergy conflict was found in the synthetic patient allergy data.",
            evidence="Zero allergy records stored for patient.",
            severity=RiskLevel.LOW,
        )

    alt_med_norm = alternative_medicine.strip().lower()
    alt_ing_norm = alternative_ingredient.strip().lower()

    for allergy in allergies:
        allergen_norm = allergy.allergen.strip().lower()
        group_members = ALLERGEN_GROUP_MAPPING.get(allergen_norm, {allergen_norm})
        is_conflict = (
            allergen_norm == alt_ing_norm
            or allergen_norm in alt_med_norm
            or any(member in alt_ing_norm or member in alt_med_norm for member in group_members)
        )

        if is_conflict:
            risk = _map_severity(allergy.severity)
            reaction_text = f" ({allergy.reaction})" if allergy.reaction else ""
            return CheckResult(
                check_name="allergy",
                status=CheckStatus.FAIL,
                reason=f"Proposed alternative '{alternative_medicine}' conflicts with recorded patient allergy '{allergy.allergen}' ({(allergy.severity or 'MODERATE').upper()} severity).",
                evidence=f"Synthetic allergy record ID {allergy.id}: Allergen={allergy.allergen}{reaction_text}, Severity={(allergy.severity or 'MODERATE').upper()}",
                severity=risk,
            )

    return CheckResult(
        check_name="allergy",
        status=CheckStatus.PASS,
        reason="No recorded allergy conflict was found in the synthetic patient allergy data.",
        evidence=f"Evaluated {len(allergies)} allergy record(s) without conflict.",
        severity=RiskLevel.LOW,
    )


def evaluate_renal_check(
    patient_exists: bool,
    renal_status: Optional[str],
    candidate_medicine: str,
    constraints: List[ClinicalConstraint],
) -> CheckResult:
    """Pure rule check evaluating candidate alternative against active synthetic RENAL clinical constraints."""
    if not patient_exists:
        return CheckResult(
            check_name="renal",
            status=CheckStatus.FAIL,
            reason="Patient record ID not found in prototype database.",
            evidence="Patient lookup returned None.",
            severity=RiskLevel.HIGH,
        )

    renal_constraints = [c for c in constraints if c.constraint_type.strip().upper() == "RENAL"]
    if not renal_constraints:
        return CheckResult(
            check_name="renal",
            status=CheckStatus.PASS,
            reason="No recorded renal conflict was found in the synthetic prototype rules.",
            evidence="No active RENAL constraint rules found for candidate medicine.",
            severity=RiskLevel.LOW,
        )

    p_renal = (renal_status or "NORMAL").strip().lower()
    if p_renal == "normal":
        return CheckResult(
            check_name="renal",
            status=CheckStatus.PASS,
            reason="No recorded renal conflict was found in the synthetic prototype rules.",
            evidence=f"Patient renal status is {p_renal.upper()}.",
            severity=RiskLevel.LOW,
        )

    for c in renal_constraints:
        rule_norm = c.constraint_rule.strip().lower()
        if p_renal in rule_norm:
            risk = _map_severity(c.severity)
            return CheckResult(
                check_name="renal",
                status=CheckStatus.FAIL,
                reason=f"Proposed alternative '{candidate_medicine}' conflicts with patient's recorded renal status '{p_renal.upper()}'. Constraint rule: {c.constraint_rule}",
                evidence=f"Synthetic clinical constraint ID {c.id}: Rule={c.constraint_rule} (Source: {c.evidence_source or 'Prototype rules'})",
                severity=risk,
            )

    return CheckResult(
        check_name="renal",
        status=CheckStatus.PASS,
        reason="No recorded renal conflict was found in the synthetic prototype rules.",
        evidence=f"Patient renal status '{p_renal.upper()}' does not trigger matching RENAL constraint.",
        severity=RiskLevel.LOW,
    )


def evaluate_hepatic_check(
    patient_exists: bool,
    hepatic_status: Optional[str],
    candidate_medicine: str,
    constraints: List[ClinicalConstraint],
) -> CheckResult:
    """Pure rule check evaluating candidate alternative against active synthetic HEPATIC clinical constraints."""
    if not patient_exists:
        return CheckResult(
            check_name="hepatic",
            status=CheckStatus.FAIL,
            reason="Patient record ID not found in prototype database.",
            evidence="Patient lookup returned None.",
            severity=RiskLevel.HIGH,
        )

    hepatic_constraints = [c for c in constraints if c.constraint_type.strip().upper() == "HEPATIC"]
    if not hepatic_constraints:
        return CheckResult(
            check_name="hepatic",
            status=CheckStatus.PASS,
            reason="No recorded hepatic conflict was found in the synthetic prototype rules.",
            evidence="No active HEPATIC constraint rules found for candidate medicine.",
            severity=RiskLevel.LOW,
        )

    p_hepatic = (hepatic_status or "NORMAL").strip().lower()
    if p_hepatic == "normal":
        return CheckResult(
            check_name="hepatic",
            status=CheckStatus.PASS,
            reason="No recorded hepatic conflict was found in the synthetic prototype rules.",
            evidence=f"Patient hepatic status is {p_hepatic.upper()}.",
            severity=RiskLevel.LOW,
        )

    for c in hepatic_constraints:
        rule_norm = c.constraint_rule.strip().lower()
        if p_hepatic in rule_norm:
            risk = _map_severity(c.severity)
            return CheckResult(
                check_name="hepatic",
                status=CheckStatus.FAIL,
                reason=f"Proposed alternative '{candidate_medicine}' conflicts with patient's recorded hepatic status '{p_hepatic.upper()}'. Constraint rule: {c.constraint_rule}",
                evidence=f"Synthetic clinical constraint ID {c.id}: Rule={c.constraint_rule} (Source: {c.evidence_source or 'Prototype rules'})",
                severity=risk,
            )

    return CheckResult(
        check_name="hepatic",
        status=CheckStatus.PASS,
        reason="No recorded hepatic conflict was found in the synthetic prototype rules.",
        evidence=f"Patient hepatic status '{p_hepatic.upper()}' does not trigger matching HEPATIC constraint.",
        severity=RiskLevel.LOW,
    )


def evaluate_pregnancy_check(
    patient_exists: bool,
    pregnancy_status: Optional[str],
    candidate_medicine: str,
    constraints: List[ClinicalConstraint],
) -> CheckResult:
    """Pure rule check evaluating candidate alternative against active synthetic PREGNANCY clinical constraints."""
    if not patient_exists:
        return CheckResult(
            check_name="pregnancy",
            status=CheckStatus.FAIL,
            reason="Patient record ID not found in prototype database.",
            evidence="Patient lookup returned None.",
            severity=RiskLevel.HIGH,
        )

    pregnancy_constraints = [c for c in constraints if c.constraint_type.strip().upper() == "PREGNANCY"]
    p_pregnancy = (pregnancy_status or "NOT_PREGNANT").strip().lower()

    if p_pregnancy == "pregnant" and pregnancy_constraints:
        c = pregnancy_constraints[0]
        risk = _map_severity(c.severity)
        return CheckResult(
            check_name="pregnancy",
            status=CheckStatus.FAIL,
            reason=f"Proposed alternative '{candidate_medicine}' is contraindicated during pregnancy. Constraint rule: {c.constraint_rule}",
            evidence=f"Synthetic clinical constraint ID {c.id}: Rule={c.constraint_rule} (Source: {c.evidence_source or 'Prototype rules'})",
            severity=risk,
        )

    return CheckResult(
        check_name="pregnancy",
        status=CheckStatus.PASS,
        reason="No recorded pregnancy conflict was found in the synthetic prototype rules.",
        evidence=f"Patient pregnancy status '{p_pregnancy.upper()}' does not trigger PREGNANCY constraint.",
        severity=RiskLevel.LOW,
    )


def evaluate_age_check(
    patient_exists: bool,
    patient_age: Optional[int],
    candidate_medicine: str,
    constraints: List[ClinicalConstraint],
) -> CheckResult:
    """Pure rule check evaluating candidate alternative against active synthetic AGE clinical constraints."""
    if not patient_exists or patient_age is None or patient_age < 0:
        return CheckResult(
            check_name="age",
            status=CheckStatus.FAIL,
            reason="Patient age is missing or invalid in prototype database.",
            evidence="Patient age record is None or missing.",
            severity=RiskLevel.HIGH,
        )

    age_constraints = [c for c in constraints if c.constraint_type.strip().upper() == "AGE"]
    if not age_constraints:
        return CheckResult(
            check_name="age",
            status=CheckStatus.PASS,
            reason="No recorded age conflict was found in the synthetic prototype rules.",
            evidence="No active AGE constraint rules found for candidate medicine.",
            severity=RiskLevel.LOW,
        )

    for c in age_constraints:
        rule_norm = c.constraint_rule.strip().lower()

        # Parse 'under <N>' or 'less than <N>' or 'below <N>'
        match_under = re.search(r"(?:under|less than|below)\s+(\d+)", rule_norm)
        if match_under:
            limit = int(match_under.group(1))
            if patient_age < limit:
                risk = _map_severity(c.severity)
                return CheckResult(
                    check_name="age",
                    status=CheckStatus.FAIL,
                    reason=f"Proposed alternative '{candidate_medicine}' conflicts with patient's age ({patient_age} years old). Constraint rule: {c.constraint_rule}",
                    evidence=f"Synthetic clinical constraint ID {c.id}: Rule={c.constraint_rule} (Source: {c.evidence_source or 'Prototype rules'})",
                    severity=risk,
                )

        # Parse 'over <N>' or 'greater than <N>' or 'above <N>'
        match_over = re.search(r"(?:over|greater than|above)\s+(\d+)", rule_norm)
        if match_over:
            limit = int(match_over.group(1))
            if patient_age > limit:
                risk = _map_severity(c.severity)
                return CheckResult(
                    check_name="age",
                    status=CheckStatus.FAIL,
                    reason=f"Proposed alternative '{candidate_medicine}' conflicts with patient's age ({patient_age} years old). Constraint rule: {c.constraint_rule}",
                    evidence=f"Synthetic clinical constraint ID {c.id}: Rule={c.constraint_rule} (Source: {c.evidence_source or 'Prototype rules'})",
                    severity=risk,
                )

    return CheckResult(
        check_name="age",
        status=CheckStatus.PASS,
        reason="No recorded age conflict was found in the synthetic prototype rules.",
        evidence=f"Patient age ({patient_age} years old) satisfies active AGE constraint thresholds.",
        severity=RiskLevel.LOW,
    )


def evaluate_drug_interaction_check(
    patient_exists: bool,
    prescribed_medications: Optional[List[PrescriptionMedication]],
    candidate_medicine: str,
    constraints: List[ClinicalConstraint],
) -> CheckResult:
    """Pure rule check evaluating candidate alternative against patient's prescribed medications for DRUG_INTERACTION constraints."""
    if not patient_exists or prescribed_medications is None:
        return CheckResult(
            check_name="drug_interaction",
            status=CheckStatus.FAIL,
            reason="Patient record or prescription medication data could not be verified for drug interaction safety.",
            evidence="Prescribed medications list is None or patient missing.",
            severity=RiskLevel.HIGH,
        )

    interaction_constraints = [
        c for c in constraints if c.constraint_type.strip().upper() == "DRUG_INTERACTION"
    ]
    if not interaction_constraints:
        return CheckResult(
            check_name="drug_interaction",
            status=CheckStatus.PASS,
            reason="No active drug interaction conflict was found in the synthetic prototype rules.",
            evidence="No active DRUG_INTERACTION constraint rules found for candidate medicine.",
            severity=RiskLevel.LOW,
        )

    for c in interaction_constraints:
        rule_norm = c.constraint_rule.strip().lower()

        for med in prescribed_medications:
            med_name_norm = med.medicine_name.strip().lower()
            ing_name_norm = med.active_ingredient.strip().lower()

            # Word-boundary exact matching to prevent false positive substring matches
            has_ing_match = bool(ing_name_norm and re.search(r"\b" + re.escape(ing_name_norm) + r"\b", rule_norm))
            has_med_match = bool(med_name_norm and re.search(r"\b" + re.escape(med_name_norm) + r"\b", rule_norm))

            if has_ing_match or has_med_match:
                risk = _map_severity(c.severity)
                return CheckResult(
                    check_name="drug_interaction",
                    status=CheckStatus.FAIL,
                    reason=f"Proposed alternative '{candidate_medicine}' has a drug interaction with patient's medication '{med.medicine_name}'. Constraint rule: {c.constraint_rule}",
                    evidence=f"Synthetic clinical constraint ID {c.id}: Rule={c.constraint_rule} (Source: {c.evidence_source or 'Prototype rules'})",
                    severity=risk,
                )

    return CheckResult(
        check_name="drug_interaction",
        status=CheckStatus.PASS,
        reason="No active drug interaction conflict was found in the synthetic prototype rules.",
        evidence=f"Evaluated {len(prescribed_medications)} prescribed medication(s) against active interaction rules without conflict.",
        severity=RiskLevel.LOW,
    )


def evaluate_dosage_check(
    patient_exists: bool,
    prescribed_medication: Optional[PrescriptionMedication],
    candidate_medicine: str,
    constraints: List[ClinicalConstraint],
) -> CheckResult:
    """Pure rule check evaluating candidate alternative dosage against active synthetic DOSAGE clinical constraints."""
    if (
        not patient_exists
        or prescribed_medication is None
        or not prescribed_medication.dose
        or not str(prescribed_medication.dose).strip()
        or not prescribed_medication.frequency
        or not str(prescribed_medication.frequency).strip()
    ):
        return CheckResult(
            check_name="dosage",
            status=CheckStatus.FAIL,
            reason="Dosage information could not be verified for the proposed substitution.",
            evidence="Prescription dose or frequency is missing or invalid.",
            severity=RiskLevel.HIGH,
        )

    dosage_constraints = [
        c for c in constraints if c.constraint_type.strip().upper() == "DOSAGE"
    ]
    if not dosage_constraints:
        return CheckResult(
            check_name="dosage",
            status=CheckStatus.PASS,
            reason="No dosage conflict was found in the synthetic prototype rules.",
            evidence="No active DOSAGE constraint rules found for candidate medicine.",
            severity=RiskLevel.LOW,
        )

    dose_str = str(prescribed_medication.dose)
    freq_str = str(prescribed_medication.frequency)
    strength_str = str(prescribed_medication.strength or "")

    single_dose_mg = _parse_mg_value(dose_str) or _parse_mg_value(strength_str)
    daily_count = _parse_daily_frequency_count(freq_str)
    total_daily_dose = single_dose_mg * daily_count

    for c in dosage_constraints:
        rule_norm = c.constraint_rule.strip().lower()

        # Maximum daily dose rule parsing (e.g. 'maximum daily dose is 4000mg' or 'maximum daily dose limit 4000mg')
        match_max_dose = re.search(r"maximum daily dose\s+(?:is|limit)?\s*(\d+(?:\.\d+)?)mg", rule_norm)
        if match_max_dose:
            max_limit = float(match_max_dose.group(1))
            if total_daily_dose > max_limit:
                risk = _map_severity(c.severity)
                return CheckResult(
                    check_name="dosage",
                    status=CheckStatus.FAIL,
                    reason=f"Proposed alternative '{candidate_medicine}' conflicts with the prescribed dosage. Constraint rule: {c.constraint_rule}",
                    evidence=f"Prescribed daily dose ({total_daily_dose:g}mg) exceeds maximum synthetic limit ({max_limit:g}mg). Synthetic clinical constraint ID {c.id}: Rule={c.constraint_rule}",
                    severity=risk,
                )

        # Frequency restriction parsing (e.g. 'once weekly only')
        if "once weekly" in rule_norm and daily_count >= 1.0:
            risk = _map_severity(c.severity)
            return CheckResult(
                check_name="dosage",
                status=CheckStatus.FAIL,
                reason=f"Proposed alternative '{candidate_medicine}' conflicts with the prescribed dosage. Constraint rule: {c.constraint_rule}",
                evidence=f"Prescribed daily frequency '{freq_str}' violates once weekly administration rule. Synthetic clinical constraint ID {c.id}: Rule={c.constraint_rule}",
                severity=risk,
            )

    return CheckResult(
        check_name="dosage",
        status=CheckStatus.PASS,
        reason="No dosage conflict was found in the synthetic prototype rules.",
        evidence="Prescription dose/frequency is within the configured synthetic dosage constraint.",
        severity=RiskLevel.LOW,
    )


def evaluate_stock_check(
    candidate_medicine: Optional[str],
    stock_records: List[MedicineStock],
    current_date: Optional[date] = None,
) -> CheckResult:
    """Pure rule check evaluating candidate alternative stock availability in synthetic database."""
    if not candidate_medicine or not candidate_medicine.strip():
        return CheckResult(
            check_name="stock",
            status=CheckStatus.FAIL,
            reason="Proposed alternative medicine name is missing; stock availability cannot be verified.",
            evidence="Missing candidate medicine name.",
            severity=RiskLevel.HIGH,
        )

    if not stock_records:
        return CheckResult(
            check_name="stock",
            status=CheckStatus.FAIL,
            reason="No usable stock is available for the proposed alternative medicine.",
            evidence="Synthetic medicine stock query returned 0 records.",
            severity=RiskLevel.HIGH,
        )

    today = current_date or date.today()

    # Usable stock requires: is_available == True, quantity_available > 0, and not expired
    usable_batches = [
        s
        for s in stock_records
        if s.is_available is True
        and s.quantity_available > 0
        and (s.expiry_date is None or s.expiry_date >= today)
    ]

    if usable_batches:
        best_batch = usable_batches[0]
        pharmacy_text = best_batch.pharmacy_location or "Main Pharmacy"
        return CheckResult(
            check_name="stock",
            status=CheckStatus.PASS,
            reason="Usable stock is available for the proposed alternative medicine.",
            evidence=f"Usable stock batch found: Batch={best_batch.batch_code}, Quantity={best_batch.quantity_available}, Expiry={best_batch.expiry_date}, Location={pharmacy_text}",
            severity=RiskLevel.LOW,
        )

    # Distinguish why stock failed
    all_expired = any(
        s.is_available is True
        and s.quantity_available > 0
        and s.expiry_date is not None
        and s.expiry_date < today
        for s in stock_records
    )

    if all_expired:
        return CheckResult(
            check_name="stock",
            status=CheckStatus.FAIL,
            reason="All available stock for the proposed alternative medicine is expired.",
            evidence=f"Found {len(stock_records)} stock record(s), but all available batches are expired.",
            severity=RiskLevel.HIGH,
        )

    all_zero_quantity = all(s.quantity_available == 0 for s in stock_records)
    if all_zero_quantity:
        return CheckResult(
            check_name="stock",
            status=CheckStatus.FAIL,
            reason="No usable stock is available for the proposed alternative medicine.",
            evidence="Stock record exists but quantity_available is zero.",
            severity=RiskLevel.HIGH,
        )

    return CheckResult(
        check_name="stock",
        status=CheckStatus.FAIL,
        reason="No usable stock is available for the proposed alternative medicine.",
        evidence="Stock record exists but is_available is False or stock is unavailable.",
        severity=RiskLevel.HIGH,
    )


def evaluate_substitution_lookup(
    request: SubstitutionRequest,
    candidates: List[MedicineAlternative],
    patient: Optional[Patient] = None,
    patient_exists: bool = True,
    allergies: Optional[List[Allergy]] = None,
    clinical_constraints: Optional[List[ClinicalConstraint]] = None,
    prescribed_medications: Optional[List[PrescriptionMedication]] = None,
    prescribed_medication: Optional[PrescriptionMedication] = None,
    stock_records: Optional[List[MedicineStock]] = None,
    current_date: Optional[date] = None,
) -> DecisionResult:
    """Evaluate substitution lookup, allergy, renal, hepatic, pregnancy, age, drug interaction, dosage, and stock safety checks for a request across candidates.

    Execution Pipeline Order:
    1. approved_alternative
    2. allergy
    3. renal
    4. hepatic
    5. pregnancy
    6. age
    7. drug_interaction
    8. dosage
    9. stock
    """
    from app.services.alternative_ranking import (
        evaluate_single_candidate,
        rank_and_select_candidate,
    )

    if not candidates:
        lookup_check = evaluate_approved_alternative_check(
            request.original_medicine, candidates
        )
        return DecisionResult(
            decision_status=DecisionStatus.NO_ALTERNATIVE,
            original_medicine=request.original_medicine,
            recommended_medicine=None,
            reason="No active approved alternative was found for the requested medicine.",
            risk_level=RiskLevel.LOW,
            requires_human_confirmation=False,
            confidence_score=1.0,
            checks=[lookup_check],
        )

    evaluations = []
    for cand in candidates:
        eval_res = evaluate_single_candidate(
            request=request,
            candidate=cand,
            all_candidates=candidates,
            patient=patient,
            patient_exists=patient_exists,
            allergies=allergies,
            clinical_constraints=clinical_constraints,
            prescribed_medications=prescribed_medications,
            prescribed_medication=prescribed_medication,
            stock_records=stock_records,
            current_date=current_date,
        )
        evaluations.append(eval_res)

    return rank_and_select_candidate(request, evaluations)


def evaluate_substitution_foundation(
    request: SubstitutionRequest,
    checks: Optional[List[CheckResult]] = None,
    proposed_alternative: Optional[str] = None,
) -> DecisionResult:
    """Pure foundation evaluation function for backward compatibility and testing."""
    check_list = checks if checks is not None else []

    has_failed = any(c.status == CheckStatus.FAIL for c in check_list)
    has_passed = any(c.status == CheckStatus.PASS for c in check_list)

    if proposed_alternative is None and not has_passed and not has_failed:
        status = DecisionStatus.NO_ALTERNATIVE
        reason = f"No suitable synthetic alternative is currently available for {request.original_medicine}."
        risk = RiskLevel.LOW
        requires_human = False
        confidence = 1.0
    elif has_failed:
        status = DecisionStatus.BLOCKED
        failed_checks = [c for c in check_list if c.status == CheckStatus.FAIL]
        reasons_text = "; ".join([c.reason for c in failed_checks])
        reason = f"Substitution blocked due to clinical/patient constraints: {reasons_text}"
        max_severity = max(
            [c.severity for c in failed_checks], key=lambda s: s.value
        )
        risk = max_severity
        requires_human = True
        confidence = 1.0
    else:
        status = DecisionStatus.RECOMMENDED
        reason = f"Alternative {proposed_alternative or request.requested_alternative} passed preliminary foundation checks."
        risk = RiskLevel.LOW
        requires_human = True
        confidence = 1.0

    return DecisionResult(
        decision_status=status,
        original_medicine=request.original_medicine,
        recommended_medicine=proposed_alternative or request.requested_alternative,
        reason=reason,
        risk_level=risk,
        requires_human_confirmation=requires_human,
        confidence_score=confidence,
        checks=check_list,
    )
