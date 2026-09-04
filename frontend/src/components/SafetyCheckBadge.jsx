import React from 'react';

const CHECK_DISPLAY_NAMES = {
  approved_alternative: '1. Approved Alternative Lookup',
  allergy: '2. Patient Allergy Contraindication',
  renal: '3. Renal Function Safety Limit',
  hepatic: '4. Hepatic Function Safety Limit',
  pregnancy: '5. Pregnancy Contraindication',
  age: '6. Age-Specific Clinical Limit',
  drug_interaction: '7. Drug-Drug Interaction Safety',
  dosage: '8. Maximum Daily Dosage Boundary',
  stock: '9. Usable Stock Availability',
};

export default function SafetyCheckBadge({ check }) {
  const isPass = check.status === 'PASS';
  const isFail = check.status === 'FAIL';
  const displayName = CHECK_DISPLAY_NAMES[check.check_name] || check.check_name;

  return (
    <div className={`safety-check-card ${isFail ? 'failed-card' : isPass ? 'passed-card' : 'unchecked-card'}`}>
      <div className="check-card-header">
        <span className="check-title">{displayName}</span>
        <div className="check-badges">
          <span className={`severity-pill severity-${check.severity.toLowerCase()}`}>
            {check.severity}
          </span>
          <span className={`status-badge ${isPass ? 'status-pass' : isFail ? 'status-fail' : 'status-skip'}`}>
            {isPass ? 'PASS' : isFail ? 'FAIL' : 'NOT CHECKED'}
          </span>
        </div>
      </div>

      <p className="check-reason">{check.reason}</p>

      {check.evidence && (
        <div className="check-evidence-box">
          <span className="evidence-label">Clinical Evidence:</span> {check.evidence}
        </div>
      )}
    </div>
  );
}
