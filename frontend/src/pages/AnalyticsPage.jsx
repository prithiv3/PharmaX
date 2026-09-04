import React, { useEffect, useState } from 'react';
import { getAnalyticsSummary } from '../services/api';
import { LoadingSpinner, ErrorAlert } from '../components/StateAlert';

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [requestId, setRequestId] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    loadAnalytics();
  }, []);

  async function loadAnalytics() {
    setLoading(true);
    setError(null);
    const res = await getAnalyticsSummary();
    setLoading(false);
    setRequestId(res.requestId);

    if (res.success) {
      setStats(res.data);
    } else {
      setError(res.error);
    }
  }

  if (loading) return <LoadingSpinner message="Computing analytics summary metrics..." />;
  if (error) return <ErrorAlert title="Analytics Load Failure" error={error} requestId={requestId} onRetry={loadAnalytics} />;
  if (!stats) return null;

  const total = stats.total_decisions_evaluated || 1;
  const statusDist = stats.status_distribution || {};
  const riskDist = stats.risk_level_distribution || {};
  const blocks = stats.safety_block_breakdown || {};

  return (
    <div className="analytics-page">
      <h2>Governance Analytics & Decision Distribution</h2>
      <p className="page-intro">
        Aggregated decision metrics and safety block distribution (`GET /api/v1/substitutions/analytics/summary`).
      </p>

      <div className="analytics-grid">
        {/* Decision Status Breakdown */}
        <div className="card">
          <h3>Decision Status Breakdown</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Count</th>
                <th>Percentage</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(statusDist).map(([status, count]) => (
                <tr key={status}>
                  <td>
                    <span className={`status-badge status-${status.toLowerCase()}`}>
                      {status}
                    </span>
                  </td>
                  <td><strong>{count}</strong></td>
                  <td>{((count / total) * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Risk Level Breakdown */}
        <div className="card">
          <h3>Risk Severity Breakdown</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Risk Level</th>
                <th>Count</th>
                <th>Percentage</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(riskDist).map(([risk, count]) => (
                <tr key={risk}>
                  <td>
                    <span className={`risk-pill risk-${risk.toLowerCase()}`}>
                      {risk}
                    </span>
                  </td>
                  <td><strong>{count}</strong></td>
                  <td>{((count / total) * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Safety Block Categories Table */}
      <div className="card mt-4">
        <h3>Safety Block Root Cause Breakdown</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Safety Check Category</th>
              <th>Blocked Count</th>
              <th>Clinical Description</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>1. Allergy Contraindications</strong></td>
              <td><span className="badge badge-danger">{blocks.allergy_blocks || 0}</span></td>
              <td>Patient recorded active allergy to candidate ingredient</td>
            </tr>
            <tr>
              <td><strong>2. Renal Function Limits</strong></td>
              <td><span className="badge badge-danger">{blocks.renal_blocks || 0}</span></td>
              <td>Renal impairment contraindication or dose adjustment requirement</td>
            </tr>
            <tr>
              <td><strong>3. Hepatic Function Limits</strong></td>
              <td><span className="badge badge-danger">{blocks.hepatic_blocks || 0}</span></td>
              <td>Hepatic impairment contraindication</td>
            </tr>
            <tr>
              <td><strong>4. Pregnancy Contraindications</strong></td>
              <td><span className="badge badge-danger">{blocks.pregnancy_blocks || 0}</span></td>
              <td>Teratogenic drug contraindication during active pregnancy</td>
            </tr>
            <tr>
              <td><strong>5. Age-Specific Limits</strong></td>
              <td><span className="badge badge-danger">{blocks.age_blocks || 0}</span></td>
              <td>Pediatric or geriatric age boundary violation</td>
            </tr>
            <tr>
              <td><strong>6. Drug Interactions</strong></td>
              <td><span className="badge badge-danger">{blocks.drug_interaction_blocks || 0}</span></td>
              <td>Severe co-prescribed drug-drug interaction conflict</td>
            </tr>
            <tr>
              <td><strong>7. Dosage Limits</strong></td>
              <td><span className="badge badge-danger">{blocks.dosage_blocks || 0}</span></td>
              <td>Maximum daily dose or frequency boundary exceeded</td>
            </tr>
            <tr>
              <td><strong>8. Usable Stock Availability</strong></td>
              <td><span className="badge badge-danger">{blocks.stock_blocks || 0}</span></td>
              <td>Zero unexpired physical stock available in pharmacy inventory</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
