# Pharmacy Substitution Decision Support System

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2+-blue.svg)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/tests-225%20passed-brightgreen.svg)]()

Production-ready academic decision support MVP providing deterministic drug substitution evaluation, human-in-the-loop pharmacist review workflows, audit trails, demographic fairness analysis, and decision governance for hospital and retail pharmacies.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Problem Statement & Solution](#problem-statement--solution)
- [Key Objectives](#key-objectives)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Deterministic 9-Check Clinical Safety Pipeline](#deterministic-9-check-clinical-safety-pipeline)
- [Deterministic 5-Tier Candidate Ranking](#deterministic-5-tier-candidate-ranking)
- [Decision Lifecycle & Pharmacist Review Workflow](#decision-lifecycle--pharmacist-review-workflow)
- [Security & Governance Hardening](#security--governance-hardening)
- [REST API Endpoints](#rest-api-endpoints)
- [Installation & Quick Start](#installation--quick-start)
- [Testing & Verification](#testing--verification)
- [Demo Scenarios](#demo-scenarios)
- [Documentation Index](#documentation-index)
- [Prototype Limitations](#prototype-limitations)

---

## Project Overview

Medication brand availability, formulation changes, and inventory shortages frequently require pharmacists to evaluate therapeutic drug substitutions. Manual substitution evaluation poses clinical risks if patient allergies, organ function limits, drug-drug interactions, pregnancy contraindications, or dosage limits are overlooked.

This system provides a **100% deterministic, auditable decision support engine** that automatically evaluates therapeutic alternatives against a strict 9-check clinical safety pipeline, selects the safest alternative, persists audit logs, supports human-in-the-loop pharmacist reviews/overrides, and tracks demographic fairness metrics across synthetic patient cohorts.

---

## Problem Statement & Solution

- **The Problem**: Manual pharmacy substitution is error-prone, time-consuming, and lacks systematic compliance audit logging. Generative AI/LLM models are unsuitable for final clinical decisions due to non-deterministic hallucinations, lack of mathematical guarantees, and opacity.
- **The Solution**: A deterministic rules engine powered by Python, FastAPI, and PostgreSQL. Every clinical check produces an explicit PASS/FAIL result, clinical reason, severity level, and evidence text. No decision is made by non-deterministic models.

---

## Key Objectives

1. **Patient Safety**: Zero unsafe substitutions recommended.
2. **Clinical Auditability**: Every decision and pharmacist review generates an immutable compliance audit trail log.
3. **Human-in-the-Loop Governance**: Mandatory pharmacist confirmation for all therapeutic substitutions, requiring explicit justifications for clinical overrides.
4. **Demographic Equity**: Built-in fairness audit metrics evaluating block rates across age, gender, and organ impairment cohorts.

---

## System Architecture

```
React 18 + Vite UI (Frontend)
       │ (HTTP REST API + X-Request-ID + X-Pharmacist-Token)
       ▼
FastAPI REST API Layer (Backend)
       │
Request Correlation & Timing Middleware
       │
Substitution Service Orchestration Layer
       │
┌───────────────────────────────┴───────────────────────────────┐
▼                                                               ▼
Deterministic 9-Check Clinical Safety Engine    Deterministic 5-Tier Candidate Ranking Engine
└───────────────────────────────┬───────────────────────────────┘
                                │ (SQLAlchemy ORM + psycopg)
                                ▼
               PostgreSQL Database (pharmacy_substitution_db)
               ├── substitution_decisions
               ├── pharmacist_reviews
               └── audit_logs
```

---

## Technology Stack

### Backend
- **Core Engine**: Python 3.13+
- **API Framework**: FastAPI, Starlette, Pydantic v2
- **ORM & Database**: SQLAlchemy 2.0, PostgreSQL, `psycopg` v3 driver
- **Testing**: `pytest`, `TestClient`

### Frontend
- **Framework**: React 18, React Router DOM v6
- **Build Tool**: Vite
- **Styling**: Vanilla CSS (Curated medical dashboard theme with CSS variables)

---

## Deterministic 9-Check Clinical Safety Pipeline

Every candidate substitution is evaluated through **9 unalterable safety checks** executed in strict sequential order:

1. `approved_alternative`: Verifies active therapeutic equivalence mapping.
2. `allergy`: Checks patient ingredient allergy contraindications.
3. `renal`: Evaluates renal impairment function limits (e.g. CrCl boundaries).
4. `hepatic`: Evaluates hepatic function contraindications.
5. `pregnancy`: Checks teratogenic drug contraindications during active pregnancy.
6. `age`: Validates pediatric (<18) or geriatric (>=65) age limits.
7. `drug_interaction`: Evaluates co-prescribed drug-drug interaction conflicts.
8. `dosage`: Verifies maximum daily dose and administration frequency limits.
9. `stock`: Checks unexpired physical inventory stock availability.

> **Rule**: If ANY safety check fails (FAIL), the candidate alternative is marked UNSAFE and will NEVER be recommended.

---

## Deterministic 5-Tier Candidate Ranking

When multiple safe candidate alternatives exist, the system selects the single best recommendation using a **5-tier priority algorithm**:

1. **Safety**: Candidate passes all 9 safety checks (`is_safe == True`).
2. **Risk Level**: Lower risk level (`LOW` < `MEDIUM` < `HIGH` < `CRITICAL`).
3. **Usable Stock**: Greater usable physical stock quantity.
4. **Alphabetical**: Alphabetical ordering by medicine name.
5. **ID Tie-Breaker**: `MedicineAlternative.id` ascending.

---

## Decision Lifecycle & Pharmacist Review Workflow

```
Evaluate Request → 9 Safety Checks → Candidate Ranking → Persist Decision & Initial Audit Log
                                                                  │
                                                                  ▼
                                                      Pharmacist Review Submission
                                                                  │
                                            ┌─────────────────────┼─────────────────────┐
                                            ▼                     ▼                     ▼
                                        APPROVED               REJECTED             OVERRIDDEN
                                                                                (Requires Reason)
                                            └─────────────────────┬─────────────────────┘
                                                                  ▼
                                                  Persist Review & Audit Log Entry
```

### Review Actions
- **`APPROVED`**: Pharmacist confirms and accepts the system recommendation.
- **`REJECTED`**: Pharmacist rejects substitution (e.g., patient requests brand name).
- **`OVERRIDDEN`**: Pharmacist clinically overrides a safety block. **Requires a non-empty `override_reason` text justification**.

---

## Security & Governance Hardening

- **Prototype Pharmacist Authorization**: `POST /api/v1/substitutions/{id}/review` requires `X-Pharmacist-Token` header (e.g. `PHARM-TOKEN-101`). Returns `401 UNAUTHORIZED` if missing or invalid.
- **Atomic Transactions**: Decision evaluation persistence and initial `AuditLog` creation execute in a single atomic PostgreSQL transaction block with clean `db.rollback()` on failure.
- **Review Concurrency Protection**: Review submissions use `.with_for_update()` pessimistic row locking on PostgreSQL.
- **Request Correlation**: `RequestCorrelationMiddleware` propagates or generates `X-Request-ID` UUID headers across all API responses.
- **Safe Exception Handling**: Global exception handler masks SQL statements, database URLs, passwords, credentials, and tracebacks, returning generic HTTP 500 error responses.
- **Log Sanitization**: Request duration logging excludes tokens, passwords, database connection strings, and request bodies.

---

## REST API Endpoints

| Method | Endpoint Path | Auth Required | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | No | Root status check |
| `GET` | `/health` | No | Application health check |
| `GET` | `/ready` | No | PostgreSQL database readiness check (`SELECT 1`) |
| `GET` | `/docs` | No | OpenAPI Swagger UI documentation |
| `POST` | `/api/v1/substitutions/evaluate` | No | Evaluate substitution request & persist decision |
| `GET` | `/api/v1/substitutions/{id}` | No | Retrieve persisted decision details & audit logs |
| `POST` | `/api/v1/substitutions/{id}/review` | **Yes** (`X-Pharmacist-Token`) | Submit pharmacist review / clinical override |
| `GET` | `/api/v1/substitutions` | No | Query decision history with pagination & filters |
| `GET` | `/api/v1/substitutions/analytics/summary` | No | Governance analytics & safety block distribution |
| `GET` | `/api/v1/substitutions/analytics/fairness` | No | Demographic cohort fairness metrics |
| `GET` | `/api/v1/substitutions/analytics/error-analysis` | No | Safety audit root cause & error analysis |

---

## Installation & Quick Start

### Prerequisites
- Windows 10/11
- Python 3.13+
- Node.js 18+
- PostgreSQL 14+ running on `localhost:5432` with database `pharmacy_substitution_db`

### 1. Database & Environment Setup
Create the PostgreSQL database:
```sql
CREATE DATABASE pharmacy_substitution_db;
```

Configure `backend/.env` (based on `.env.example`):
```env
PROJECT_NAME="Pharmacy Substitution Decision Support System"
DATABASE_URL="postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/pharmacy_substitution_db"
```

### 2. Backend Setup & Data Seeding
```powershell
# Navigate to backend directory
cd backend

# Seed synthetic population data into PostgreSQL
py scripts/seed_data.py

# Start FastAPI development server
py -m uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup & Startup
```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Testing & Verification

### Run Complete Backend Pytest Suite
```powershell
py -m pytest -W default -ra backend/tests
```
- **Verified Result**: `225 passed in 11.73s` (0 failures, 0 warnings).

### Run Frontend Production Build
```powershell
cd frontend
cmd.exe /c "npm run build"
```
- **Verified Result**: `Built cleanly in 1.27s` (0 errors, 0 warnings).

---

## Demo Scenarios

| Scenario | Patient | Medicine / Request | Expected Result | Primary Check Verified |
| --- | --- | --- | --- | --- |
| **A: Safe Substitution** | `PAT-0001` | Lisinopril 10mg Capsule | `RECOMMENDED` / `NEEDS_REVIEW` | All 9 Checks PASS |
| **B: Allergy Block** | `PAT-0002` | Amoxicillin 500mg Capsule | `BLOCKED` | `allergy` FAIL (Penicillin) |
| **C: Pregnancy Block** | `PAT-0003` | Losartan -> Valsartan 80mg | `BLOCKED` | `pregnancy` FAIL (Teratogenic) |
| **D: Stock Block** | `PAT-0005` | Metformin -> Gliclazide 80mg | `BLOCKED` | `stock` FAIL (Zero Stock) |
| **E: Pharmacist Approval** | `PAT-0001` | Decision Record #1 | Status -> `APPROVED` | Pharmacist Review Workflow |
| **F: Pharmacist Rejection** | `PAT-0001` | Decision Record #2 | Status -> `REJECTED` | Pharmacist Review Workflow |
| **G: Pharmacist Override** | `PAT-0002` | Decision Record #3 | Status -> `OVERRIDDEN` | Clinical Override Reason Enforced |

---

## Documentation Index

- [Architecture Guide](docs/ARCHITECTURE.md) — System flowcharts, component layers, & sequence diagrams.
- [Database Schema Guide](docs/DATABASE.md) — Detailed documentation for all 9 PostgreSQL tables.
- [API Reference](docs/API.md) — Complete endpoint documentation with request/response schemas.
- [Live Demonstration Guide](docs/DEMO_GUIDE.md) — 5–10 minute live demonstration script & talking points.
- [Viva Preparation Guide](docs/VIVA.md) — 35+ technical Q&As and elevator pitches.

---

## Prototype Limitations

1. **Prototype Authentication**: Uses header token validation (`X-Pharmacist-Token`) suitable for academic MVP testing. Production deployment requires OAuth2/OIDC with JWT signatures.
2. **Synthetic Data**: Clinical rules and patient data are synthetically generated for demonstration and academic evaluation.
