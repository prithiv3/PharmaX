import React, { useState, useEffect, useRef } from 'react';
import { evaluateSubstitution, lookupPreset } from '../services/api';
import SafetyCheckBadge from '../components/SafetyCheckBadge';
import { LoadingSpinner, ErrorAlert } from '../components/StateAlert';

const SYNTHETIC_PRESETS = [
  {
    name: 'Safe Substitution (PAT-0001)',
    patient_code: 'PAT-0001',
    prescription_code: 'RX-0001',
    expected_medicine: 'Lisinopril 10mg Tablet',
    requested_alternative: '',
  },
  {
    name: 'Severe Allergy Block (PAT-0002)',
    patient_code: 'PAT-0002',
    prescription_code: 'RX-0002',
    expected_medicine: 'Amoxicillin 500mg Capsule',
    requested_alternative: '',
  },
  {
    name: 'Pregnancy Block (PAT-0003)',
    patient_code: 'PAT-0003',
    prescription_code: 'RX-0003',
    expected_medicine: 'Losartan 50mg Tablet',
    requested_alternative: '',
  },
  {
    name: 'Stock Depletion Block (PAT-0005)',
    patient_code: 'PAT-0005',
    prescription_code: 'RX-0005',
    expected_medicine: 'Metformin 500mg Tablet',
    requested_alternative: 'Gliclazide 80mg Tablet',
  },
];

export default function EvaluatePage() {
  const [patientId, setPatientId] = useState('');
  const [prescriptionId, setPrescriptionId] = useState('');
  const [prescriptionMedicationId, setPrescriptionMedicationId] = useState('');
  const [originalMedicine, setOriginalMedicine] = useState('');
  const [requestedAlternative, setRequestedAlternative] = useState('');

  const [loadingPreset, setLoadingPreset] = useState(false);
  const [activePresetCode, setActivePresetCode] = useState('PAT-0001');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [requestId, setRequestId] = useState(null);
  const [result, setResult] = useState(null);

  // Version refs to eliminate asynchronous race conditions
  const presetReqVersionRef = useRef(0);
  const evalReqVersionRef = useRef(0);

  // Helper to immediately clear stale evaluation results & errors
  function clearEvaluationState() {
    setResult(null);
    setError(null);
    setRequestId(null);
  }

  // Handle manual form field modifications
  function handleFieldChange(setter) {
    return (e) => {
      clearEvaluationState();
      setter(e.target.value);
    };
  }

  async function applyPreset(preset) {
    // REQUIREMENT 1: Immediately clear stale evaluation results & errors when switching presets
    clearEvaluationState();

    // REQUIREMENT 3: Increment version to prevent stale async responses from overwriting state
    const currentVersion = ++presetReqVersionRef.current;

    setLoadingPreset(true);
    setActivePresetCode(preset.patient_code);

    const res = await lookupPreset(preset.patient_code, preset.prescription_code);

    // If another preset was clicked while waiting, discard this stale response
    if (currentVersion !== presetReqVersionRef.current) {
      return;
    }

    setLoadingPreset(false);

    if (res.success && res.data) {
      setPatientId(String(res.data.patient_id));
      setPrescriptionId(String(res.data.prescription_id));
      setPrescriptionMedicationId(String(res.data.prescription_medication_id));
      setOriginalMedicine(res.data.medicine_name || preset.expected_medicine);
      setRequestedAlternative(preset.requested_alternative || '');
    } else {
      setError(res.error || `Failed to dynamically resolve IDs for ${preset.patient_code} / ${preset.prescription_code}.`);
    }
  }

  useEffect(() => {
    applyPreset(SYNTHETIC_PRESETS[0]);
  }, []);

  async function handleEvaluate(e) {
    e.preventDefault();

    // REQUIREMENT 4: Clear previous result and set evaluation version before submitting
    clearEvaluationState();
    const currentEvalVersion = ++evalReqVersionRef.current;

    setLoading(true);

    const payload = {
      patient_id: parseInt(patientId, 10),
      prescription_id: parseInt(prescriptionId, 10),
      prescription_medication_id: parseInt(prescriptionMedicationId, 10),
      original_medicine: originalMedicine.trim(),
      requested_alternative: requestedAlternative.trim() || undefined,
    };

    const res = await evaluateSubstitution(payload);

    // REQUIREMENT 3 & 5: Ignore response if a newer evaluation or preset request was triggered
    if (currentEvalVersion !== evalReqVersionRef.current) {
      return;
    }

    setLoading(false);
    setRequestId(res.requestId);

    if (res.success) {
      setResult(res.data);
    } else {
      setError(res.error);
    }
  }

  return (
    <div className="evaluate-page">
      <h2>Evaluate Drug Substitution Request</h2>
      <p className="page-intro">
        Submits request to backend 9-check deterministic safety pipeline (`POST /api/v1/substitutions/evaluate`).
      </p>

      {/* Preset Buttons */}
      <div className="preset-bar">
        <span className="preset-label">Quick Synthetic Test Scenarios:</span>
        {SYNTHETIC_PRESETS.map((preset, index) => (
          <button
            key={index}
            type="button"
            className={`btn btn-sm ${activePresetCode === preset.patient_code ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => applyPreset(preset)}
            disabled={loadingPreset || loading}
          >
            {preset.name}
          </button>
        ))}
        {loadingPreset && <span className="text-muted ml-2">(Resolving database IDs...)</span>}
      </div>

      <div className="evaluate-layout">
        {/* Form Card */}
        <div className="card form-card">
          <h3>Request Parameters</h3>
          <form onSubmit={handleEvaluate}>
            <div className="form-group">
              <label>Patient ID (Database Primary Key):</label>
              <input
                type="number"
                className="form-control"
                value={patientId}
                onChange={handleFieldChange(setPatientId)}
                min="1"
                required
                placeholder="Resolving dynamically..."
              />
            </div>

            <div className="form-group">
              <label>Prescription ID (Database Primary Key):</label>
              <input
                type="number"
                className="form-control"
                value={prescriptionId}
                onChange={handleFieldChange(setPrescriptionId)}
                min="1"
                required
                placeholder="Resolving dynamically..."
              />
            </div>

            <div className="form-group">
              <label>Prescription Medication ID (Database Primary Key):</label>
              <input
                type="number"
                className="form-control"
                value={prescriptionMedicationId}
                onChange={handleFieldChange(setPrescriptionMedicationId)}
                min="1"
                required
                placeholder="Resolving dynamically..."
              />
            </div>

            <div className="form-group">
              <label>Original Medicine Name:</label>
              <input
                type="text"
                className="form-control"
                value={originalMedicine}
                onChange={handleFieldChange(setOriginalMedicine)}
                required
              />
            </div>

            <div className="form-group">
              <label>Requested Alternative (Optional):</label>
              <input
                type="text"
                className="form-control"
                value={requestedAlternative}
                onChange={handleFieldChange(setRequestedAlternative)}
                placeholder="Leave blank for automatic lookup..."
              />
            </div>

            <button type="submit" className="btn btn-primary btn-block" disabled={loading || loadingPreset}>
              {loading ? 'Evaluating Safety Rules...' : 'Run Safety Evaluation'}
            </button>
          </form>
        </div>

        {/* Results View */}
        <div className="results-container">
          {loading && <LoadingSpinner message="Executing 9-check deterministic clinical safety pipeline..." />}
          {error && <ErrorAlert title="Evaluation Failed" error={error} requestId={requestId} />}

          {result && (
            <div className="result-wrapper">
              <div className={`decision-banner decision-${result.decision_status.toLowerCase()}`}>
                <div className="banner-main">
                  <span className="banner-status">{result.decision_status}</span>
                  <span className={`risk-pill risk-${result.risk_level.toLowerCase()}`}>
                    {result.risk_level} RISK
                  </span>
                </div>
                <p className="banner-reason">{result.reason}</p>

                <div className="banner-details">
                  <div><strong>Original:</strong> {result.original_medicine}</div>
                  <div><strong>Recommended:</strong> {result.recommended_medicine || 'None (Substitution Blocked)'}</div>
                  <div><strong>Confidence Score:</strong> {(result.confidence_score * 100).toFixed(0)}%</div>
                  <div><strong>Human Confirmation Required:</strong> {result.requires_human_confirmation ? 'YES' : 'NO'}</div>
                </div>
              </div>

              <h3>Evaluated Safety Checks (Strict Pipeline Order)</h3>
              <div className="safety-checks-grid">
                {result.checks.map((check, idx) => (
                  <SafetyCheckBadge key={idx} check={check} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
