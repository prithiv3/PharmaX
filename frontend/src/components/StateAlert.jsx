import React from 'react';

export function LoadingSpinner({ message = 'Evaluating clinical safety rules...' }) {
  return (
    <div className="state-container loading-state">
      <div className="spinner"></div>
      <p>{message}</p>
    </div>
  );
}

export function ErrorAlert({ title = 'API Error Encountered', error, requestId, onRetry }) {
  return (
    <div className="state-container error-state">
      <div className="error-icon">!</div>
      <div className="error-content">
        <h3>{title}</h3>
        <p className="error-detail">{error || 'An unexpected error occurred while communicating with the backend.'}</p>
        {requestId && requestId !== 'N/A' && (
          <p className="request-id-tag">
            Correlation Request ID: <code>{requestId}</code>
          </p>
        )}
        {onRetry && (
          <button className="btn btn-secondary btn-sm" onClick={onRetry}>
            Retry Request
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ title = 'No Data Found', message = 'No records match your query filters.' }) {
  return (
    <div className="state-container empty-state">
      <div className="empty-icon">📂</div>
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
}
