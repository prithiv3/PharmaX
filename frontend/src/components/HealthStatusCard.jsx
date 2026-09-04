import React, { useState, useEffect } from 'react';
import { getHealthStatus, getRootStatus } from '../services/api';

export default function HealthStatusCard() {
  const [healthStatus, setHealthStatus] = useState(null);
  const [rootStatus, setRootStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);

    const [healthRes, rootRes] = await Promise.all([
      getHealthStatus(),
      getRootStatus()
    ]);

    if (healthRes.success && rootRes.success) {
      setHealthStatus(healthRes.data);
      setRootStatus(rootRes.data);
    } else {
      setError(healthRes.error || rootRes.error || 'Failed to connect to FastAPI backend');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div className="card" id="backend-health-card">
      <h2 className="card-title">Backend Connectivity & Health</h2>
      
      {loading && (
        <div className="status-pill status-loading" id="health-loading">
          <span className="dot dot-loading"></span>
          Connecting to FastAPI backend...
        </div>
      )}

      {!loading && error && (
        <div>
          <div className="status-pill status-unhealthy" id="health-error">
            <span className="dot dot-unhealthy"></span>
            Backend Disconnected ({error})
          </div>
          <button 
            onClick={fetchStatus}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              background: 'rgba(56, 189, 248, 0.2)',
              border: '1px solid #38bdf8',
              color: '#38bdf8',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            Retry Connection
          </button>
        </div>
      )}

      {!loading && !error && healthStatus && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div>
            <span style={{ color: '#8b949e', fontSize: '0.9rem' }}>FastAPI GET /health Status: </span>
            <div className="status-pill status-healthy" id="health-status-value">
              <span className="dot dot-healthy"></span>
              {healthStatus.status}
            </div>
          </div>

          {rootStatus && (
            <div style={{ marginTop: '0.5rem', background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '6px' }}>
              <p style={{ fontSize: '0.85rem', color: '#8b949e' }}>Root API Response (GET /):</p>
              <code style={{ color: '#38bdf8', fontSize: '0.85rem' }}>
                {JSON.stringify(rootStatus, null, 2)}
              </code>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
