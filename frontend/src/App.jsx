import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import Header from './components/Header';
import Navigation from './components/Navigation';

import DashboardPage from './pages/DashboardPage';
import EvaluatePage from './pages/EvaluatePage';
import DecisionDetailPage from './pages/DecisionDetailPage';
import HistoryPage from './pages/HistoryPage';
import AnalyticsPage from './pages/AnalyticsPage';
import FairnessPage from './pages/FairnessPage';
import ErrorAnalysisPage from './pages/ErrorAnalysisPage';

export default function App() {
  const [pharmacistToken, setPharmacistToken] = useState('PHARM-TOKEN-101');

  return (
    <Router>
      <div className="app-container">
        <Header pharmacistToken={pharmacistToken} setPharmacistToken={setPharmacistToken} />
        <Navigation />

        <main className="main-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/evaluate" element={<EvaluatePage />} />
            <Route path="/decisions/:id" element={<DecisionDetailPage pharmacistToken={pharmacistToken} />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/fairness" element={<FairnessPage />} />
            <Route path="/error-analysis" element={<ErrorAnalysisPage />} />
          </Routes>
        </main>

        <footer className="footer">
          <p>
            Pharmacy Substitution Decision Support System &copy; 2026 Academic Prototype | PostgreSQL Backend Dialect | 9-Check Clinical Safety Pipeline
          </p>
        </footer>
      </div>
    </Router>
  );
}
