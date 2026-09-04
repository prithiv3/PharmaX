import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAnalyticsSummary } from '../services/api';
import { LoadingSpinner, ErrorAlert } from '../components/StateAlert';

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [requestId, setRequestId] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    loadSummary();
  }, []);

  async function loadSummary() {
    setLoading(true);
    setError(null);
    const res = await getAnalyticsSummary();
    setLoading(false);

    if (res.success) {
      setStats(res.data);
      setRequestId(res.requestId);
    } else {
      setError(res.error);
      setRequestId(res.requestId);
    }
  }

  if (loading) return <LoadingSpinner message="Loading dashboard governance metrics..." />;
  if (error) return <ErrorAlert title="Dashboard Load Error" error={error} requestId={requestId} onRetry={loadSummary} />;
  if (!stats) return null;

  const statusDist = stats.status_distribution || {};
  const riskDist = stats.risk_level_distribution || {};
  const blocks = stats.safety_block_breakdown || {};

  return (
    <div className="dashboard-page">
      <div className="page-header-banner">
        <div>
          <h2>Pharmacist System Dashboard</h2>
          <p>Real-time clinical safety statistics & decision support metrics (PostgreSQL Backend)</p>
        </div>
        <Link to="/evaluate" className="btn btn-primary">
          + Evaluate New Request
        </Link>
      </div>

      {/* KPI Cards Grid */}
      <div className="kpi-grid">
        <div className="kpi-card kpi-total">
          <div className="kpi-title">Total Evaluated</div>
          <div className="kpi-value">{stats.total_decisions_evaluated}</div>
          <div className="kpi-sub">Database Records</div>
        </div>

        <div className="kpi-card kpi-recommended">
          <div className="kpi-title">Recommended</div>
          <div className="kpi-value">{statusDist.RECOMMENDED || 0}</div>
          <div className="kpi-sub">Safe Substitutions</div>
        </div>

        <div className="kpi-card kpi-blocked">
          <div className="kpi-title">Safety Blocked</div>
          <div className="kpi-value">{statusDist.BLOCKED || 0}</div>
          <div className="kpi-sub">Contraindicated</div>
        </div>

        <div className="kpi-card kpi-review">
          <div className="kpi-title">Needs Review</div>
          <div className="kpi-value">{statusDist.NEEDS_REVIEW || 0}</div>
          <div className="kpi-sub">Pharmacist Check</div>
        </div>

        <div className="kpi-card kpi-approved">
          <div className="kpi-title">Pharmacist Approved</div>
          <div className="kpi-value">{statusDist.APPROVED || 0}</div>
          <div className="kpi-sub">Confirmed</div>
        </div>

        <div className="kpi-card kpi-override">
          <div className="kpi-title">Clinical Overrides</div>
          <div className="kpi-value">{stats.total_pharmacist_overrides || 0}</div>
          <div className="kpi-sub">Human Interventions</div>
        </div>
      </div>

      {/* Breakdown Grids */}
      <div className="dashboard-grid">
        {/* Risk Distribution Card */}
        <div className="panel-card">
          <h3>Risk Level Distribution</h3>
          <div className="progress-list">
            <div className="progress-item">
              <div className="progress-header">
                <span>LOW Risk</span>
                <span>{riskDist.LOW || 0}</span>
              </div>
              <div className="progress-bar-bg">
                <div
                  className="progress-bar bar-low"
                  style={{ width: `${stats.total_decisions_evaluated ? ((riskDist.LOW || 0) / stats.total_decisions_evaluated) * 100 : 0}%` }}
                ></div>
              </div>
            </div>

            <div className="progress-item">
              <div className="progress-header">
                <span>MEDIUM Risk</span>
                <span>{riskDist.MEDIUM || 0}</span>
              </div>
              <div className="progress-bar-bg">
                <div
                  className="progress-bar bar-medium"
                  style={{ width: `${stats.total_decisions_evaluated ? ((riskDist.MEDIUM || 0) / stats.total_decisions_evaluated) * 100 : 0}%` }}
                ></div>
              </div>
            </div>

            <div className="progress-item">
              <div className="progress-header">
                <span>HIGH Risk</span>
                <span>{riskDist.HIGH || 0}</span>
              </div>
              <div className="progress-bar-bg">
                <div
                  className="progress-bar bar-high"
                  style={{ width: `${stats.total_decisions_evaluated ? ((riskDist.HIGH || 0) / stats.total_decisions_evaluated) * 100 : 0}%` }}
                ></div>
              </div>
            </div>

            <div className="progress-item">
              <div className="progress-header">
                <span>CRITICAL Risk</span>
                <span>{riskDist.CRITICAL || 0}</span>
              </div>
              <div className="progress-bar-bg">
                <div
                  className="progress-bar bar-critical"
                  style={{ width: `${stats.total_decisions_evaluated ? ((riskDist.CRITICAL || 0) / stats.total_decisions_evaluated) * 100 : 0}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Safety Block Categories Card */}
        <div className="panel-card">
          <h3>Safety Block Categories</h3>
          <div className="block-category-grid">
            <div className="block-chip">
              <span className="chip-name">Allergy Contraindications:</span>
              <span className="chip-count">{blocks.allergy_blocks || 0}</span>
            </div>
            <div className="block-chip">
              <span className="chip-name">Renal Function Limits:</span>
              <span className="chip-count">{blocks.renal_blocks || 0}</span>
            </div>
            <div className="block-chip">
              <span className="chip-name">Hepatic Function Limits:</span>
              <span className="chip-count">{blocks.hepatic_blocks || 0}</span>
            </div>
            <div className="block-chip">
              <span className="chip-name">Pregnancy Contraindications:</span>
              <span className="chip-count">{blocks.pregnancy_blocks || 0}</span>
            </div>
            <div className="block-chip">
              <span className="chip-name">Age-Specific Limits:</span>
              <span className="chip-count">{blocks.age_blocks || 0}</span>
            </div>
            <div className="block-chip">
              <span className="chip-name">Drug Interactions:</span>
              <span className="chip-count">{blocks.drug_interaction_blocks || 0}</span>
            </div>
            <div className="block-chip">
              <span className="chip-name">Dosage Limits:</span>
              <span className="chip-count">{blocks.dosage_blocks || 0}</span>
            </div>
            <div className="block-chip">
              <span className="chip-name">Stock Depletions:</span>
              <span className="chip-count">{blocks.stock_blocks || 0}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
