import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getDecisionDetails } from '../services/api';
import SafetyCheckBadge from '../components/SafetyCheckBadge';
import ReviewModal from '../components/ReviewModal';
import { LoadingSpinner, ErrorAlert } from '../components/StateAlert';

export default function DecisionDetailPage({ pharmacistToken }) {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [requestId, setRequestId] = useState(null);
  const [decision, setDecision] = useState(null);
  const [showReviewModal, setShowReviewModal] = useState(false);

  useEffect(() => {
    loadDetails();
  }, [id]);

  async function loadDetails() {
    setLoading(true);
    setError(null);
    const res = await getDecisionDetails(id);
    setLoading(false);
    setRequestId(res.requestId);

    if (res.success) {
      setDecision(res.data);
    } else {
      setError(res.error);
    }
  }

  if (loading) return <LoadingSpinner message={`Retrieving decision details #${id} from PostgreSQL database...`} />;
  if (error) return <ErrorAlert title="Decision Detail Error" error={error} requestId={requestId} onRetry={loadDetails} />;
  if (!decision) return null;

  return (
    <div className="decision-detail-page">
      <div className="page-header-banner">
        <div>
          <Link to="/history" className="back-link">&larr; Back to Decision History</Link>
          <h2>Substitution Decision Record #{decision.id}</h2>
          <p>Created At: {new Date(decision.created_at).toLocaleString()}</p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowReviewModal(true)}>
          + Submit Pharmacist Review
        </button>
      </div>

      {/* Decision Summary Card */}
      <div className={`decision-banner decision-${decision.decision_status.toLowerCase()}`}>
        <div className="banner-main">
          <span className="banner-status">{decision.decision_status}</span>
          <span className={`risk-pill risk-${decision.risk_level.toLowerCase()}`}>
            {decision.risk_level} RISK
          </span>
        </div>
        <p className="banner-reason">{decision.reason}</p>

        <div className="banner-details">
          <div><strong>Patient ID:</strong> {decision.patient_id}</div>
          <div><strong>Original Medicine:</strong> {decision.original_medicine}</div>
          <div><strong>Recommended Alternative:</strong> {decision.recommended_medicine || 'None (Blocked)'}</div>
          <div><strong>Confidence Score:</strong> {(decision.confidence_score * 100).toFixed(0)}%</div>
        </div>
      </div>

      {/* Safety Checks */}
      <div className="detail-section">
        <h3>Evaluated Safety Checks ({decision.checks.length})</h3>
        <div className="safety-checks-grid">
          {decision.checks.map((check, idx) => (
            <SafetyCheckBadge key={idx} check={check} />
          ))}
        </div>
      </div>

      {/* Review History */}
      <div className="detail-section">
        <h3>Pharmacist Review History ({decision.reviews.length})</h3>
        {decision.reviews.length === 0 ? (
          <p className="text-muted">No pharmacist reviews submitted yet for this record.</p>
        ) : (
          <div className="history-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Pharmacist Code</th>
                  <th>Review Status</th>
                  <th>Override Reason</th>
                  <th>Notes</th>
                  <th>Reviewed At</th>
                </tr>
              </thead>
              <tbody>
                {decision.reviews.map((rev) => (
                  <tr key={rev.id}>
                    <td>#{rev.id}</td>
                    <td><code>{rev.pharmacist_code}</code></td>
                    <td>
                      <span className={`status-badge status-${rev.review_status.toLowerCase()}`}>
                        {rev.review_status}
                      </span>
                    </td>
                    <td>{rev.override_reason || '-'}</td>
                    <td>{rev.review_notes || '-'}</td>
                    <td>{new Date(rev.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Audit Log Trail */}
      <div className="detail-section">
        <h3>Compliance Audit Log Trail ({decision.audit_logs.length})</h3>
        <div className="history-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Action</th>
                <th>Actor Code</th>
                <th>Previous Status</th>
                <th>New Status</th>
                <th>Audit Reason</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {decision.audit_logs.map((audit) => (
                <tr key={audit.id}>
                  <td>#{audit.id}</td>
                  <td><code>{audit.action}</code></td>
                  <td>{audit.actor_code ? <code>{audit.actor_code}</code> : 'SYSTEM'}</td>
                  <td>{audit.previous_status || '-'}</td>
                  <td>{audit.new_status}</td>
                  <td>{audit.reason}</td>
                  <td>{new Date(audit.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showReviewModal && (
        <ReviewModal
          decisionId={decision.id}
          initialStatus={decision.decision_status}
          pharmacistToken={pharmacistToken}
          onClose={() => setShowReviewModal(false)}
          onSuccess={loadDetails}
        />
      )}
    </div>
  );
}
