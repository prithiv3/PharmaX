import React from 'react';
import { NavLink } from 'react-router-dom';

export default function Navigation() {
  return (
    <nav className="navigation-bar">
      <NavLink to="/" end className={({ isActive }) => (isActive ? 'nav-tab active' : 'nav-tab')}>
        Dashboard
      </NavLink>
      <NavLink to="/evaluate" className={({ isActive }) => (isActive ? 'nav-tab active' : 'nav-tab')}>
        Evaluate Request
      </NavLink>
      <NavLink to="/history" className={({ isActive }) => (isActive ? 'nav-tab active' : 'nav-tab')}>
        Decision History
      </NavLink>
      <NavLink to="/analytics" className={({ isActive }) => (isActive ? 'nav-tab active' : 'nav-tab')}>
        Governance Analytics
      </NavLink>
      <NavLink to="/fairness" className={({ isActive }) => (isActive ? 'nav-tab active' : 'nav-tab')}>
        Demographic Fairness
      </NavLink>
      <NavLink to="/error-analysis" className={({ isActive }) => (isActive ? 'nav-tab active' : 'nav-tab')}>
        Safety & Error Audit
      </NavLink>
    </nav>
  );
}
