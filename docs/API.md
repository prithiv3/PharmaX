# REST API Reference — Pharmacy Substitution Decision Support API

Complete REST API documentation for all 11 endpoints implemented in FastAPI.

Base URL: `http://localhost:8000`

---

## 1. System Health & Readiness Endpoints

### `GET /`
- **Purpose**: System identification & root status check.
- **Authentication**: None.
- **Headers Returned**: `X-Request-ID`.
- **Response `200 OK`**:
```json
{
  "message": "Pharmacy Substitution Decision Support API",
  "status": "running"
}
```

### `GET /health`
- **Purpose**: Application liveness health check.
- **Authentication**: None.
- **Response `200 OK`**:
```json
{
  "status": "healthy"
}
```

### `GET /ready`
- **Purpose**: PostgreSQL database readiness check (executes `SELECT 1`).
- **Authentication**: None.
- **Response `200 OK`**:
```json
{
  "status": "ready",
  "database": "connected"
}
```
- **Response `503 Service Unavailable`**:
```json
{
  "detail": "Database service unavailable."
}
```

### `GET /docs`
- **Purpose**: Interactive OpenAPI Swagger UI documentation.
- **Authentication**: None.

---

## 2. Substitution Decision Engine Endpoints

### `POST /api/v1/substitutions/evaluate`
- **Purpose**: Evaluates candidate alternatives against 9 clinical safety checks, ranks alternatives deterministically, and persists decision + initial audit log to PostgreSQL.
- **Authentication**: None.
- **Request Body**: `SubstitutionEvaluationRequest`
```json
{
  "patient_id": 1,
  "prescription_id": 1,
  "prescription_medication_id": 1,
  "original_medicine": "Amoxicillin 500mg Capsule",
  "requested_alternative": null
}
```
- **Response `200 OK`**: `SubstitutionDecisionResponse`
```json
{
  "id": 105,
  "patient_id": 1,
  "prescription_id": 1,
  "prescription_medication_id": 1,
  "original_medicine": "Amoxicillin 500mg Capsule",
  "recommended_medicine": "Amoxicillin 500mg Oral Suspension",
  "decision_status": "RECOMMENDED",
  "risk_level": "LOW",
  "confidence_score": 1.0,
  "requires_human_confirmation": true,
  "reason": "Evaluated 1 candidate alternatives. Selected safest candidate 'Amoxicillin 500mg Oral Suspension' passing all 9 safety checks.",
  "checks": [
    {
      "check_name": "approved_alternative",
      "status": "PASS",
      "severity": "LOW",
      "reason": "Candidate drug is an approved alternative formulation.",
      "evidence": "Therapeutic category match."
    },
    ...
  ],
  "created_at": "2026-08-27T10:45:00Z"
}
```

---

### `GET /api/v1/substitutions/{decision_id}`
- **Purpose**: Retrieves a persisted decision record with 9 safety check results, pharmacist review history, and compliance audit trail logs.
- **Authentication**: None.
- **Path Parameter**: `decision_id` (integer).
- **Response `200 OK`**: `SubstitutionDecisionDetailResponse`
```json
{
  "id": 105,
  "patient_id": 1,
  "prescription_id": 1,
  "prescription_medication_id": 1,
  "original_medicine": "Amoxicillin 500mg Capsule",
  "recommended_medicine": "Amoxicillin 500mg Oral Suspension",
  "decision_status": "APPROVED",
  "risk_level": "LOW",
  "confidence_score": 1.0,
  "requires_human_confirmation": true,
  "reason": "Evaluated 1 candidate alternatives...",
  "checks": [...],
  "reviews": [
    {
      "id": 12,
      "pharmacist_code": "PHARM-101",
      "review_status": "APPROVED",
      "override_reason": null,
      "review_notes": "Clinical confirmation.",
      "created_at": "2026-08-27T10:50:00Z"
    }
  ],
  "audit_logs": [
    {
      "id": 204,
      "action": "DECISION_EVALUATED",
      "actor_code": "SYSTEM",
      "previous_status": null,
      "new_status": "RECOMMENDED",
      "reason": "Evaluated 1 candidate alternatives.",
      "created_at": "2026-08-27T10:45:00Z"
    },
    {
      "id": 205,
      "action": "PHARMACIST_REVIEW",
      "actor_code": "PHARM-101",
      "previous_status": "RECOMMENDED",
      "new_status": "APPROVED",
      "reason": "Pharmacist PHARM-101 reviewed decision. Status: APPROVED.",
      "created_at": "2026-08-27T10:50:00Z"
    }
  ],
  "created_at": "2026-08-27T10:45:00Z"
}
```
- **Response `404 Not Found`**:
```json
{
  "detail": "Substitution decision record not found."
}
```

---

### `POST /api/v1/substitutions/{decision_id}/review`
- **Purpose**: Submits a human-in-the-loop pharmacist review or clinical override. Executes pessimistic row locking (`FOR UPDATE`) on PostgreSQL.
- **Authentication**: **Required Header**: `X-Pharmacist-Token` (e.g. `PHARM-TOKEN-101`).
- **Request Body**: `PharmacistReviewRequest`
```json
{
  "pharmacist_code": "PHARM-101",
  "review_status": "OVERRIDDEN",
  "override_reason": "Desensitization therapy completed under specialist supervision.",
  "review_notes": "Specialist approval documented."
}
```
- **Response `200 OK`**: `SubstitutionDecisionDetailResponse`
- **Response `400 Bad Request`**:
```json
{
  "detail": "An explicit override reason is required when selecting OVERRIDDEN status."
}
```
- **Response `401 Unauthorized`**:
```json
{
  "detail": "Unauthorized: Invalid or missing X-Pharmacist-Token header."
}
```

---

### `GET /api/v1/substitutions`
- **Purpose**: Queries persisted decision records with pagination and filters.
- **Authentication**: None.
- **Query Parameters**:
  - `patient_id` (optional integer)
  - `decision_status` (optional enum: `RECOMMENDED`, `BLOCKED`, `NEEDS_REVIEW`, `APPROVED`, `REJECTED`, `OVERRIDDEN`)
  - `risk_level` (optional enum: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
  - `limit` (optional integer, 1 to 100, default 20)
  - `offset` (optional integer, >= 0, default 0)
- **Response `200 OK`**: `SubstitutionDecisionListResponse`
```json
{
  "total": 120,
  "limit": 20,
  "offset": 0,
  "items": [ ... ]
}
```

---

## 3. Analytics & Governance Endpoints

### `GET /api/v1/substitutions/analytics/summary`
- **Purpose**: Aggregate decision governance statistics, risk distributions, safety block category counts, and override metrics.
- **Authentication**: None.
- **Response `200 OK`**: `AnalyticsSummaryResponse`

---

### `GET /api/v1/substitutions/analytics/fairness`
- **Purpose**: Demographic cohort fairness audit metrics across Age Groups, Gender, and Organ Impairment. Includes synthetic population disclaimer.
- **Authentication**: None.
- **Response `200 OK`**: `PopulationFairnessResponse`

---

### `GET /api/v1/substitutions/analytics/error-analysis`
- **Purpose**: Safety audit root cause breakdown, risk severity, confidence scores, and block rate metrics.
- **Authentication**: None.
- **Response `200 OK`**: `ErrorAnalysisResponse`
