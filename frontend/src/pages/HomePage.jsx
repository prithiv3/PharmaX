import React from 'react';
import HealthStatusCard from '../components/HealthStatusCard';

export default function HomePage() {
  return (
    <div className="home-page" id="home-page-container">
      <section className="card">
        <h2 className="card-title">Project Overview</h2>
        <p style={{ color: '#8b949e', marginBottom: '1rem' }}>
          Welcome to the initial prototype for the <strong>Pharmacy Substitution Decision Support System</strong>.
          This decision-support tool assists pharmacists in assessing medicine substitution options for patients with multiple prescriptions while evaluating clinical constraints, allergies, inventory, and prescriber rules.
        </p>

        <div className="disclaimer-box" id="safety-disclaimer">
          <div className="disclaimer-title">⚠️ Clinical & Safety Disclaimer</div>
          <div className="disclaimer-text">
            This project is an academic prototype using synthetic data and synthetic rules.
            It is not intended for real-world clinical prescribing, dispensing, or medicine-substitution decisions.
            A qualified pharmacist/human must remain the final decision maker for all high-impact actions.
          </div>
        </div>
      </section>

      <section>
        <HealthStatusCard />
      </section>

      <section className="card">
        <h2 className="card-title">Architecture Roadmap</h2>
        <ul style={{ paddingLeft: '1.25rem', color: '#8b949e', lineHeight: '1.8' }}>
          <li><strong style={{ color: '#34d399' }}>✓ Phase 1:</strong> Architecture Initialization, FastAPI Backend, React Frontend & Pytest Suite.</li>
          <li><strong style={{ color: '#8b949e' }}>○ Phase 2:</strong> Synthetic Data Engine & Patient Profile Integration.</li>
          <li><strong style={{ color: '#8b949e' }}>○ Phase 3:</strong> Rule Engine (Clinical Constraints, Allergies, Stock & Prescriber Rules).</li>
          <li><strong style={{ color: '#8b949e' }}>○ Phase 4:</strong> Decision Support Interface, Pharmacist Approval/Override Workflow.</li>
          <li><strong style={{ color: '#8b949e' }}>○ Phase 5:</strong> Bias & Fairness Evaluation & Metrics Dashboard.</li>
        </ul>
      </section>
    </div>
  );
}
