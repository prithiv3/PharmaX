import React, { useEffect, useState } from 'react';
import { getErrorAnalysisMetrics } from '../services/api';
import { LoadingSpinner, ErrorAlert } from '../components/StateAlert';

export default function ErrorAnalysisPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [requestId, setRequestId] = useState(null);
  const [audit, setAudit] = useState(null);

  useEffect(() => {
    loadErrorAnalysis();
  }, []);

  async function loadErrorAnalysis() {
    setLoading(true);
    setError(null);
    const res = await getErrorAnalysisMetrics();
    setLoading(false);
    setRequestId(res.requestId);

    if (res.success) {
      setAudit(res.data);
    } else {
      setError(res.error);
    }
  }

  if (loading) return <LoadingSpinner message="Generating safety audit and error analysis metrics..." />;
  if (error) return <ErrorAlert title="Error Audit Load Failure" error={error} requestId={requestId} onRetry={loadErrorAnalysis} />;
  if (!audit) return null;

  const rootCauses = audit.root_cause_breakdown || {};
  const riskBreakdown = audit.risk_level_breakdown || {};

  return (
    <div className="error-analysis-page">
      <h2>Clinical Safety Audit & Root Cause Error Analysis</h2>
      <p className="page-intro">
        Safety block root causes and decision confidence audit metrics (`GET /api/v1/substitutions/analytics/error-analysis`).
      </p>

      {/* Distinction Banner */}
      <div className="info-banner mb-4">
        <strong>Classification Note:</strong> Safety-rule blocks (e.g. Allergy or Pregnancy contraindications) reflect deterministic clinical safety enforcement and are distinctly separated from application runtime errors.
      </div>

      {/* KPI Row */}
      <div className="kpi-grid mb-4">
        <div className="kpi-card kpi-total">
          <div className="kpi-title">Decisions Analyzed</div>
          <div className="kpi-value">{audit.total_decisions_analyzed}</div>
        </div>

        <div className="kpi-card kpi-blocked">
          <div className="kpi-title">Total Safety Blocks</div>
          <div className="kpi-value">{audit.total_blocks}</div>
        </div>

        <div className="kpi-card kpi-override">
          <div className="kpi-title">Overall Block Rate</div>
          <div className="kpi-value">{(audit.block_rate * 100).toFixed(1)}%</div>
        </div>

        <div className="kpi-card kpi-recommended">
          <div className="kpi-title">Mean Decision Confidence</div>
          <div className="kpi-value">{(audit.average_confidence_score * 100).toFixed(0)}%</div>
        </div>
      </div>

      <div className="analytics-grid mb-4">
        {/* Root Cause Table */}
        <div className="card">
          <h3>Root Cause Safety Block Categories</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Root Cause Category</th>
                <th>Block Count</th>
                <th>Percentage of Blocks</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(rootCauses).map(([category, count]) => (
                <tr key={category}>
                  <td><strong>{category}</strong></td>
                  <td>{count}</td>
                  <td>{audit.total_blocks ? ((count / audit.total_blocks) * 100).toFixed(1) : 0}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Risk Level Distribution */}
        <div className="card">
          <h3>Risk Level Classification</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Risk Level</th>
                <th>Count</th>
                <th>Percentage</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(riskBreakdown).map(([risk, count]) => (
                <tr key={risk}>
                  <td>
                    <span className={`risk-pill risk-${risk.toLowerCase()}`}>
                      {risk}
                    </span>
                  </td>
                  <td>{count}</td>
                  <td>{audit.total_decisions_analyzed ? ((count / audit.total_decisions_analyzed) * 100).toFixed(1) : 0}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
