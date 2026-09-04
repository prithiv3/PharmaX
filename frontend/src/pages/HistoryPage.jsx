import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getDecisionHistory } from '../services/api';
import { LoadingSpinner, ErrorAlert, EmptyState } from '../components/StateAlert';

export default function HistoryPage() {
  const [patientIdFilter, setPatientIdFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');

  const [limit] = useState(15);
  const [offset, setOffset] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [requestId, setRequestId] = useState(null);
  const [data, setData] = useState({ total: 0, items: [] });

  useEffect(() => {
    loadHistory();
  }, [offset, statusFilter, riskFilter]);

  async function loadHistory() {
    setLoading(true);
    setError(null);

    const params = {
      limit,
      offset,
      patient_id: patientIdFilter ? parseInt(patientIdFilter, 10) : undefined,
      decision_status: statusFilter || undefined,
      risk_level: riskFilter || undefined,
    };

    const res = await getDecisionHistory(params);
    setLoading(false);
    setRequestId(res.requestId);

    if (res.success) {
      setData(res.data);
    } else {
      setError(res.error);
    }
  }

  function handleFilterSubmit(e) {
    e.preventDefault();
    setOffset(0);
    loadHistory();
  }

  function handleClearFilters() {
    setPatientIdFilter('');
    setStatusFilter('');
    setRiskFilter('');
    setOffset(0);
  }

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(data.total / limit) || 1;

  return (
    <div className="history-page">
      <h2>Persisted Decision History & Audit Records</h2>
      <p className="page-intro">
        Query and filter persisted substitution decisions stored in PostgreSQL database (`GET /api/v1/substitutions`).
      </p>

      {/* Filter Bar */}
      <form onSubmit={handleFilterSubmit} className="filter-card">
        <div className="filter-inputs">
          <div className="form-group inline-group">
            <label>Patient ID:</label>
            <input
              type="number"
              className="form-control form-control-sm"
              value={patientIdFilter}
              onChange={(e) => setPatientIdFilter(e.target.value)}
              placeholder="e.g. 1"
              min="1"
            />
          </div>

          <div className="form-group inline-group">
            <label>Decision Status:</label>
            <select
              className="form-control form-control-sm"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">All Statuses</option>
              <option value="RECOMMENDED">RECOMMENDED</option>
              <option value="BLOCKED">BLOCKED</option>
              <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
              <option value="APPROVED">APPROVED</option>
              <option value="REJECTED">REJECTED</option>
              <option value="OVERRIDDEN">OVERRIDDEN</option>
            </select>
          </div>

          <div className="form-group inline-group">
            <label>Risk Level:</label>
            <select
              className="form-control form-control-sm"
              value={riskFilter}
              onChange={(e) => {
                setRiskFilter(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">All Risk Levels</option>
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>
        </div>

        <div className="filter-actions">
          <button type="submit" className="btn btn-primary btn-sm">Filter</button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleClearFilters}>Reset</button>
        </div>
      </form>

      {/* State Renderers */}
      {loading && <LoadingSpinner message="Querying PostgreSQL decision history database..." />}
      {error && <ErrorAlert title="History Load Failure" error={error} requestId={requestId} onRetry={loadHistory} />}

      {!loading && !error && data.items.length === 0 && (
        <EmptyState title="No Decision Records Found" message="No database records matched your active filter criteria." />
      )}

      {/* Table Render */}
      {!loading && !error && data.items.length > 0 && (
        <>
          <div className="history-table-wrapper card">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Patient ID</th>
                  <th>Original Medicine</th>
                  <th>Recommended Alternative</th>
                  <th>Status</th>
                  <th>Risk Level</th>
                  <th>Evaluated At</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td>#{item.id}</td>
                    <td>PAT-{String(item.patient_id).padStart(4, '0')}</td>
                    <td>{item.original_medicine}</td>
                    <td>{item.recommended_medicine || <span className="text-muted">None (Blocked)</span>}</td>
                    <td>
                      <span className={`status-badge status-${item.decision_status.toLowerCase()}`}>
                        {item.decision_status}
                      </span>
                    </td>
                    <td>
                      <span className={`risk-pill risk-${item.risk_level.toLowerCase()}`}>
                        {item.risk_level}
                      </span>
                    </td>
                    <td>{new Date(item.created_at).toLocaleString()}</td>
                    <td>
                      <Link to={`/decisions/${item.id}`} className="btn btn-outline btn-xs">
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="pagination-bar">
            <span className="pagination-info">
              Showing page {currentPage} of {totalPages} ({data.total} total records)
            </span>
            <div className="pagination-buttons">
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
              >
                &larr; Previous Page
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= data.total}
              >
                Next Page &rarr;
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
