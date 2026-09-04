import React, { useEffect, useState } from 'react';
import { getFairnessMetrics } from '../services/api';
import { LoadingSpinner, ErrorAlert } from '../components/StateAlert';

export default function FairnessPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [requestId, setRequestId] = useState(null);
  const [fairness, setFairness] = useState(null);

  useEffect(() => {
    loadFairness();
  }, []);

  async function loadFairness() {
    setLoading(true);
    setError(null);
    const res = await getFairnessMetrics();
    setLoading(false);
    setRequestId(res.requestId);

    if (res.success) {
      setFairness(res.data);
    } else {
      setError(res.error);
    }
  }

  if (loading) return <LoadingSpinner message="Evaluating demographic cohort fairness metrics..." />;
  if (error) return <ErrorAlert title="Fairness Metrics Error" error={error} requestId={requestId} onRetry={loadFairness} />;
  if (!fairness) return null;

  return (
    <div className="fairness-page">
      <h2>Demographic Cohort Fairness & Bias Analysis</h2>
      <p className="page-intro">
        Audit of substitution decision behavior across demographic cohorts (`GET /api/v1/substitutions/analytics/fairness`).
      </p>

      {/* Synthetic Population Audit Disclaimer Banner */}
      <div className="disclaimer-banner">
        <strong>Synthetic Population Audit Disclaimer:</strong> Metrics displayed below are calculated strictly on synthetic patient population data for academic evaluation purposes and do not represent real-world clinical patient populations.
      </div>

      {/* Age Group Cohorts */}
      <div className="card mb-4">
        <h3>Age Group Demographic Cohorts</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Age Cohort Segment</th>
              <th>Total Evaluations</th>
              <th>Recommended Count</th>
              <th>Blocked Count</th>
              <th>Block Rate</th>
              <th>Pharmacist Overrides</th>
            </tr>
          </thead>
          <tbody>
            {(fairness.age_group_metrics || []).map((segment, idx) => (
              <tr key={idx}>
                <td><strong>{segment.segment_name}</strong></td>
                <td>{segment.total_evaluations}</td>
                <td>{segment.recommended_count}</td>
                <td>{segment.blocked_count}</td>
                <td>
                  <span className={`badge ${segment.block_rate > 0.25 ? 'badge-warning' : 'badge-info'}`}>
                    {(segment.block_rate * 100).toFixed(1)}%
                  </span>
                </td>
                <td>{segment.override_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Gender Cohorts */}
      <div className="card mb-4">
        <h3>Gender Demographic Cohorts</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Gender Segment</th>
              <th>Total Evaluations</th>
              <th>Recommended Count</th>
              <th>Blocked Count</th>
              <th>Block Rate</th>
              <th>Pharmacist Overrides</th>
            </tr>
          </thead>
          <tbody>
            {(fairness.gender_metrics || []).map((segment, idx) => (
              <tr key={idx}>
                <td><strong>{segment.segment_name}</strong></td>
                <td>{segment.total_evaluations}</td>
                <td>{segment.recommended_count}</td>
                <td>{segment.blocked_count}</td>
                <td>
                  <span className={`badge ${segment.block_rate > 0.25 ? 'badge-warning' : 'badge-info'}`}>
                    {(segment.block_rate * 100).toFixed(1)}%
                  </span>
                </td>
                <td>{segment.override_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Organ Impairment Cohorts */}
      <div className="card mb-4">
        <h3>Organ Impairment Cohorts</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Organ Function Segment</th>
              <th>Total Evaluations</th>
              <th>Recommended Count</th>
              <th>Blocked Count</th>
              <th>Block Rate</th>
              <th>Pharmacist Overrides</th>
            </tr>
          </thead>
          <tbody>
            {(fairness.organ_impairment_metrics || []).map((segment, idx) => (
              <tr key={idx}>
                <td><strong>{segment.segment_name}</strong></td>
                <td>{segment.total_evaluations}</td>
                <td>{segment.recommended_count}</td>
                <td>{segment.blocked_count}</td>
                <td>
                  <span className={`badge ${segment.block_rate > 0.25 ? 'badge-warning' : 'badge-info'}`}>
                    {(segment.block_rate * 100).toFixed(1)}%
                  </span>
                </td>
                <td>{segment.override_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Disparity Audit Notes */}
      {fairness.fairness_disparity_notes && fairness.fairness_disparity_notes.length > 0 && (
        <div className="card notes-card">
          <h3>Demographic Disparity Audit Notes</h3>
          <ul>
            {fairness.fairness_disparity_notes.map((note, idx) => (
              <li key={idx}>{note}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
