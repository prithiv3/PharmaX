# 70% Progress Report — Pharmacy Substitution Decision Support System

**Project:** Pharmacy Substitution Decision Support System
**Team:** PharmaX | **Stack:** FastAPI · PostgreSQL · React 18 · SQLAlchemy
**Report Date:** 29 September 2026 | **Milestone:** M1 Complete + M2 In Progress

---

## 1. Problem & Motivation

Manual therapeutic drug substitution under brand-shortage or formulary-change conditions is a leading source of preventable adverse drug events. Pharmacists working under time pressure routinely overlook patient allergies, organ-function limits, pregnancy contraindications, and drug-drug interactions. Generative AI / LLMs are categorically unsuitable for this domain — they cannot guarantee zero hallucinations, strict execution order, or legal auditability.

Our system delivers a **100% deterministic, fully auditable clinical decision support engine** backed by PostgreSQL, with a React governance dashboard and human-in-the-loop pharmacist review workflows.

---

## 2. What Has Been Built (70% Complete)

### 2.1 Deterministic 9-Check Clinical Safety Engine ✅

Every candidate drug alternative is evaluated through **9 sequential, unalterable safety checks**. A single FAIL immediately marks the candidate UNSAFE — it is never recommended.

| # | Check | Clinical Basis |
|---|---|---|
| 1 | `approved_alternative` | Therapeutic equivalence mapping |
| 2 | `allergy` | Patient allergen vs. active ingredient match |
| 3 | `renal` | eGFR threshold vs. `min_egfr` constraint |
| 4 | `hepatic` | Hepatic impairment contraindication flag |
| 5 | `pregnancy` | Teratogenic drug contraindication |
| 6 | `age` | Pediatric (<18) and geriatric (≥65) age bounds |
| 7 | `drug_interaction` | Co-prescribed active ingredient conflict check |
| 8 | `dosage` | Prescribed dose × frequency vs. `max_daily_dose_mg` |
| 9 | `stock` | Unexpired physical inventory `usable_stock > 0` |

**Verified:** 4 live demo scenarios — allergy block (PAT-0002), pregnancy block (PAT-0003), stock depletion (PAT-0005), full safe pass (PAT-0001).

### 2.2 Deterministic 5-Tier Candidate Ranking ✅

When multiple alternatives pass all 9 checks, one is selected by strict deterministic priority:

1. All 9 checks PASS → 2. Lowest risk level (LOW < MEDIUM < HIGH < CRITICAL) → 3. Highest usable stock → 4. Alphabetical medicine name → 5. Primary key ascending

### 2.3 PostgreSQL Data Architecture ✅

10 normalised tables: `patients`, `allergies`, `prescriptions`, `prescription_medications`, `medicine_alternatives`, `clinical_constraints`, `medicine_stocks`, `substitution_decisions`, `pharmacist_reviews`, `audit_logs`.

Key hardening:
- **Atomic transactions**: decision + initial AuditLog written in a single `BEGIN … COMMIT` block with `db.rollback()` on failure
- **Pessimistic row locking**: pharmacist review submission executes `SELECT … FOR UPDATE` preventing race conditions
- **Connection pool**: `pool_size=10`, `max_overflow=5`, `pool_timeout=10s`, `pool_recycle=1800s` (sourced from `Settings`)

### 2.4 FastAPI REST API — 11 Endpoints ✅

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` `/ready` | Liveness + DB readiness (SELECT 1) |
| POST | `/api/v1/substitutions/evaluate` | 9-check pipeline + persist + audit |
| GET | `/api/v1/substitutions/{id}` | Decision + reviews + audit trail |
| POST | `/api/v1/substitutions/{id}/review` | Pharmacist review / override (auth required) |
| GET | `/api/v1/substitutions` | Paginated decision history with filters |
| GET | `/analytics/summary` | Risk distributions + block breakdowns |
| GET | `/analytics/fairness` | Demographic cohort bias + parity metrics |
| GET | `/analytics/error-analysis` | Root cause + confidence score analysis |

### 2.5 Human-in-the-Loop Pharmacist Review Workflow ✅

Pharmacists submit `APPROVED`, `REJECTED`, or `OVERRIDDEN` actions via authenticated endpoint (`X-Pharmacist-Token` header). **Clinical overrides require a non-empty `override_reason`** — enforced at both client (React validation) and server (FastAPI 400 Bad Request). Every review appends an immutable `AuditLog` row.

### 2.6 Demographic Fairness & Bias Reporting ✅ *(Enhanced — M2 Deliverable)*

`GET /analytics/fairness` now returns per-cohort formal bias metrics across three dimensions:

| Metric | Definition |
|---|---|
| `baseline_block_rate` | Population-wide block rate across all cohorts |
| `statistical_parity_gap` | Cohort block rate − baseline (positive = over-blocked) |
| `error_rate_disparity` | Cohort block rate / baseline (ratio; 1.0 = parity) |
| `max_intra_dimension_gap` | Max |block_rateᵢ − block_rateⱼ| within same dimension |

A `BiasAuditSummary` object aggregates cross-dimension max parity gaps, max error-rate disparity ratios, a `fairness_threshold_breached` flag (`|gap| > 0.05`), and a `breached_segments` list — enabling automated governance alerts.

### 2.7 Capacity Constraints & Graceful Fallback ✅ *(M2 Deliverable)*

| Constraint | Value | Mechanism |
|---|---|---|
| Max concurrent evaluations | 50 | `threading.Semaphore` → HTTP 429 + `Retry-After: 5` |
| Review rate limit | 30 req/min | Documented in `Settings`; enforcement planned M2.5 |
| Evaluation timeout | 15 s | `EVALUATION_TIMEOUT_SECONDS` in `Settings` |
| DB pool exhaustion | pool_timeout = 10 s | SQLAlchemy QueuePool → propagates as 503 |
| Analytics DB unreachable | Graceful 503 JSON | `get_db_with_fallback()` yields `None` → structured response |

### 2.8 Security & Middleware Hardening ✅

- `RequestCorrelationMiddleware` attaches `X-Request-ID` UUID to every response
- Global exception handler masks DB URLs, credentials, SQL, and tracebacks
- `pool_pre_ping=True` detects stale connections before use
- `check_db_connection()` catches `SQLAlchemyError` gracefully

### 2.9 Test Suite ✅

**225 pytest tests — 0 failures, 0 warnings** (verified in 11.73 s).

Frontend production build: **clean in 1.27 s, 0 errors**.

---

## 3. Remaining Work (30%)

| Milestone | Deliverable | Status |
|---|---|---|
| M2.1 | JWT OIDC authentication replacing header token | Designed |
| M2.2 | RBAC role hierarchy (`PHARMACIST → SENIOR → DIRECTOR`) | Designed |
| M2.3 | Override state machine + dual sign-off for CRITICAL risk | Designed |
| M2.4 | SLA timer + lapse handler for CRITICAL overrides (4 h) | Planned |
| M2.5 | Rate-limit enforcement middleware + HL7/FHIR EHR hook | Planned |

The full RBAC specification (role taxonomy, permission matrix, override state machine, JWT payload design, audit trail field requirements) is documented in [`docs/RBAC_OVERRIDE_WORKFLOWS.md`](../docs/RBAC_OVERRIDE_WORKFLOWS.md).

---

## 4. Key Design Decisions

**Why deterministic rules, not ML/AI?** Clinical safety demands 100% reproducible, legally auditable outcomes. LLMs cannot guarantee zero hallucination rates or strict execution order — both are non-negotiable for drug substitution.

**Why PostgreSQL over SQLite/NoSQL?** ACID guarantees, `SELECT FOR UPDATE` pessimistic locking, foreign key constraint enforcement, and enterprise-grade connection pooling are required for concurrent pharmacist review submissions and immutable audit trails.

**Why human-in-the-loop mandatory?** Every evaluation sets `requires_human_confirmation=True`. No substitution is dispensed without explicit pharmacist sign-off — the system is decision *support*, not autonomous authority.

---

> **Repo:** github.com/prithiv3/PharmaX · `main` · **Tests:** 225 passed
