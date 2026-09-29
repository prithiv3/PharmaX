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

### Test Suite Overview — 226 Tests, 0 Failures

All 226 tests run against a live PostgreSQL database using FastAPI `TestClient`. No mocks substitute the database engine — tests reflect real SQL behaviour.

```powershell
# Run complete test suite
& "backend\.venv\Scripts\python.exe" -m pytest backend/tests -v --tb=short
# Result: 226 passed in ~7s
```

### Test Module Breakdown

| Module | Tests | Scope |
| --- | --- | --- |
| `test_allergy_check.py` | 18 | Unit: allergen normalization, case-insensitive matching, multi-allergen patients |
| `test_age_check.py` | 16 | Unit: pediatric (<18), geriatric (≥65), boundary values (17/18, 64/65) |
| `test_clinical_checks.py` | 22 | Unit: renal eGFR boundaries, hepatic flags, pregnancy contraindications |
| `test_dosage_check.py` | 19 | Unit: dose × freq vs. max_daily_dose_mg — exact boundary and overflow cases |
| `test_drug_interaction.py` | 21 | Unit: comma-separated interacting_drugs, partial/full ingredient match |
| `test_stock_check.py` | 17 | Unit: zero stock, expired stock, multi-batch usable stock aggregation |
| `test_alternative_ranking.py` | 28 | Unit: 5-tier ranking determinism, tie-breaking, risk-level ordering |
| `test_substitution_engine.py` | 14 | Integration: full 9-check pipeline, short-circuit on first FAIL |
| `test_decision_persistence_and_review.py` | 24 | Integration: DB write + audit log atomicity, pessimistic lock, review workflow |
| `test_api_contract.py` | 15 | Contract: all 11 endpoint schemas, X-Request-ID propagation, log sanitization |
| `test_production_security.py` | 22 | Security: 401 on missing token, global exception masking, transaction rollback |
| `test_decision_analytics.py` | 18 | Analytics: summary, fairness, error-analysis response schema validation |
| `test_population_fairness_and_error_analysis.py` | 12 | Fairness: statistical_parity_gap, error_rate_disparity, BiasAuditSummary fields |
| `test_full_stack_integration.py` | 19 | E2E: 7 clinical scenarios from API call to DB record to audit trail |
| Others (health, models, seeds, e2e, alternative_lookup) | 21 | Health checks, ORM model integrity, seed data, E2E coverage |

### Error Boundary Test Coverage

Every failure mode is explicitly unit-tested and contract-verified:

| Error Class | HTTP Code | Test | Mechanism |
| --- | --- | --- | --- |
| Missing `X-Pharmacist-Token` | 401 | `test_production_security.py::test_1` | `get_authenticated_pharmacist` dependency |
| `OVERRIDDEN` with no reason | 400 | `test_decision_persistence_and_review.py` | FastAPI body validation + service guard |
| Non-existent `patient_id` | 404 | `test_substitution_api.py` | Service-layer `get_patient_by_id` check |
| Non-existent `decision_id` | 404 | `test_api_contract.py` | Repository `get_substitution_decision_by_id` |
| Prescription ≠ patient mismatch | 400 | `test_substitution_api.py` | Service cross-ownership validation |
| DB connection failure | 503 | `test_api_contract.py::test_4` | `patch(check_db_connection, False)` |
| Internal unhandled exception | 500 | `test_production_security.py` | Global exception handler — no traceback/creds leaked |
| Capacity exceeded | 429 | `test_production_security.py` | `capacity_guard` semaphore dependency |
| Invalid token literal | 401 | `test_production_security.py` | Token denylist in `get_authenticated_pharmacist` |
| `limit` out of range (0 or 101) | 422 | `test_api_contract.py` | FastAPI Query validator |

### Transaction Rollback Testing

`test_production_security.py` directly tests the atomic `create_substitution_decision_and_audit()` repository function:
- Mocks `db.add(AuditLog)` to raise `SQLAlchemyError` mid-transaction
- Asserts `db.rollback()` fires and no orphaned `SubstitutionDecision` row exists
- Confirms decision count unchanged after forced failure

### Concurrency / Row-Lock Verification

`test_decision_persistence_and_review.py` verifies `SELECT … FOR UPDATE`:
- Two sequential review submissions on the same decision ID succeed without overwriting
- `PharmacistReview` table receives both rows; `AuditLog` records both events
- Lock acquisition and release tested via sequential `TestClient` calls

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
- [Database Schema Guide](docs/DATABASE.md) — Detailed documentation for all 10 PostgreSQL tables.
- [API Reference](docs/API.md) — Complete endpoint documentation with request/response schemas.
- [Live Demonstration Guide](docs/DEMO_GUIDE.md) — 5-10 minute live demonstration script & talking points.
- [Viva Preparation Guide](docs/VIVA.md) — 35+ technical Q&As and elevator pitches.
- [RBAC & Override Workflows](docs/RBAC_OVERRIDE_WORKFLOWS.md) — Role taxonomy, permission matrix, override state machine, dual sign-off specification.
- [70% Progress Report](docs/PROGRESS_REPORT_70.md) — AI-evaluator milestone progress report.
- [100% Completion Report](docs/COMPLETION_REPORT_100.md) — Full project completion report with test breakdown and design rationale.

---

## Prototype Limitations

1. **Prototype Authentication**: Uses header token validation (`X-Pharmacist-Token`) suitable for academic MVP testing. Production deployment requires OAuth2/OIDC with JWT signatures.
2. **Synthetic Data**: Clinical rules and patient data are synthetically generated for demonstration and academic evaluation.
