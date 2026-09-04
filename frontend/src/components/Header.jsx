import React, { useEffect, useState } from 'react';
import { getReadinessStatus } from '../services/api';

export default function Header({ pharmacistToken, setPharmacistToken }) {
  const [dbStatus, setDbStatus] = useState('checking');

  useEffect(() => {
    async function checkReadiness() {
      const res = await getReadinessStatus();
      if (res.success && res.data.status === 'ready') {
        setDbStatus('connected');
      } else {
        setDbStatus('disconnected');
      }
    }
    checkReadiness();
    const interval = setInterval(checkReadiness, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="header">
      <div className="header-brand">
        <div className="logo-icon">Rx</div>
        <div>
          <h1 className="header-title">Pharmacy Substitution Support</h1>
          <p className="header-subtitle">Deterministic Clinical Safety Engine & Audit Trail Governance</p>
        </div>
      </div>

      <div className="header-controls">
        <div className="db-badge-container">
          <span className="db-label">Database:</span>
          <span className={`db-badge ${dbStatus}`}>
            <span className="pulse-dot"></span>
            {dbStatus === 'connected' ? 'PostgreSQL Connected' : dbStatus === 'checking' ? 'Checking...' : 'DB Offline'}
          </span>
        </div>

        <div className="token-input-group">
          <label htmlFor="token-input" className="token-label">Pharmacist Auth Token:</label>
          <input
            id="token-input"
            type="text"
            className="token-input"
            value={pharmacistToken}
            onChange={(e) => setPharmacistToken(e.target.value)}
            placeholder="PHARM-TOKEN-101"
            title="Prototype X-Pharmacist-Token header sent with review requests"
          />
        </div>
      </div>
    </header>
  );
}
