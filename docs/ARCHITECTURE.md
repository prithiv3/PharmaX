# System Architecture — Pharmacy Substitution Decision Support System

This document describes the high-level architecture, component layers, data flows, and sequence flowcharts for the Pharmacy Substitution Decision Support System.

---

## High-Level Component Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     React 18 + Vite Web Application                     │
│    (Dashboard, Evaluate, History, Analytics, Fairness, Error Audit)     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (HTTP REST API + X-Request-ID + X-Pharmacist-Token)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       FastAPI REST API Layer (v1)                       │
│    (Request Routing, Parameter Validation, Security Headers, Middleware)│
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Substitution Service Orchestration                   │
│   (Coordinates Engine, Repositories, Atomic Transactions, & Audit Logs) │
└───────────────────┬─────────────────────────────────┬───────────────────┘
                    │                                 │
                    ▼                                 ▼
┌──────────────────────────────────────┐   ┌──────────────────────────────┐
│  Deterministic 9-Check Safety Engine │   │ Deterministic Candidate      │
│  (Allergy, Renal, Hepatic, Age, etc) │   │ 5-Tier Priority Ranking      │
└──────────────────────────────────────┘   └──────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SQLAlchemy ORM Repositories                      │
│            (Pessimistic Row Locking FOR UPDATE & Transactions)          │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (psycopg DBAPI Driver)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              PostgreSQL Database (pharmacy_substitution_db)             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Decision Evaluation Data Flow Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Pharmacist as Browser Client (React UI)
    participant API as FastAPI Router
    participant Service as Substitution Service
    participant Engine as Deterministic 9-Check Engine
    participant Ranker as Candidate Ranker
    participant Repo as Decision Repository
    participant DB as PostgreSQL Database

    Pharmacist->>API: POST /api/v1/substitutions/evaluate {patient_id, prescription_id, original_medicine}
    API->>API: Middleware attaches X-Request-ID
    API->>Service: evaluate_substitution_request(request)
    Service->>Repo: Fetch Patient, Prescription, & Candidate Alternatives
    Repo->>DB: SELECT patient, allergies, constraints FROM PostgreSQL
    DB-->>Repo: Return patient clinical context
    
    Service->>Engine: Run 9 Safety Checks for each candidate alternative
    note over Engine: 1.approved 2.allergy 3.renal 4.hepatic<br/>5.pregnancy 6.age 7.interaction 8.dosage 9.stock
    Engine-->>Service: SafetyCheckResults (PASS/FAIL per check)
    
    Service->>Ranker: Rank candidates passing all 9 safety checks
    note over Ranker: 1.All 9 Pass 2.Lower Risk 3.Stock<br/>4.Alphabetical 5.ID Ascending
    Ranker-->>Service: Best Candidate Recommendation
    
    Service->>Repo: create_substitution_decision_and_audit(decision, audit)
    Repo->>DB: BEGIN Transaction -> INSERT SubstitutionDecision & AuditLog -> COMMIT
    DB-->>Repo: Transaction Committed (ID #105)
    Repo-->>Service: Saved Decision Entity
    Service-->>API: SubstitutionDecisionResponse
    API-->>Pharmacist: HTTP 200 OK + Decision JSON + X-Request-ID
```

---

## 2. Pharmacist Review & Clinical Override Workflow Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Pharmacist as Licensed Pharmacist
    participant UI as React Review Modal
    participant API as FastAPI Review Router
    participant Security as Auth Token Guard
    participant Service as Substitution Service
    participant Repo as Decision Repository
    participant DB as PostgreSQL Database

    Pharmacist->>UI: Selects "OVERRIDDEN" -> Types override_reason -> Clicks Submit
    UI->>API: POST /api/v1/substitutions/105/review (Header: X-Pharmacist-Token: PHARM-TOKEN-101)
    API->>Security: Depends(get_authenticated_pharmacist)
    Security-->>API: Authenticated Pharmacist Token Context
    
    API->>Service: submit_pharmacist_review(decision_id, review_data)
    Service->>Repo: get_substitution_decision_for_update(decision_id)
    Repo->>DB: SELECT * FROM substitution_decisions WHERE id=105 FOR UPDATE
    DB-->>Repo: Row Locked Exclusively
    
    Service->>Repo: Save PharmacistReview & AuditLog (Action: PHARMACIST_REVIEW)
    Repo->>DB: INSERT PharmacistReview & UPDATE decision_status to OVERRIDDEN -> COMMIT
    DB-->>Repo: Transaction Committed & Lock Released
    Repo-->>Service: Updated Decision Entity
    Service-->>API: SubstitutionDecisionDetailResponse
    API-->>UI: HTTP 200 OK + Updated Record
    UI-->>Pharmacist: Refreshes UI showing updated status & audit trail log entry
```

---

## 3. Governance Analytics Data Flow Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Governance as Pharmacy Manager / Auditor
    participant UI as Governance Analytics Page
    participant API as FastAPI Analytics Router
    participant Service as Analytics Service
    participant Repo as Analytics Repository
    participant DB as PostgreSQL Database

    Governance->>UI: Navigates to /analytics or /fairness
    UI->>API: GET /api/v1/substitutions/analytics/fairness
    API->>Service: get_population_fairness_metrics()
    Service->>Repo: fetch_decision_cohort_breakdowns()
    Repo->>DB: SELECT age, gender, renal/hepatic metrics GROUP BY cohort
    DB-->>Repo: Aggregated database record sets
    Repo-->>Service: DemographicCohortMetrics
    Service->>Service: Calculate disparity metrics & audit notes
    Service-->>API: PopulationFairnessResponse
    API-->>UI: HTTP 200 OK + Fairness JSON
    UI-->>Governance: Renders demographic fairness tables & synthetic disclaimer banner
```
