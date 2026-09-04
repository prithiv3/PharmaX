# Viva Defense Preparation Guide — Pharmacy Substitution Decision Support System

This document prepares candidates for academic viva defense examinations, technical panel questions, and project presentations.

---

## Technical Elevator Pitches

### 10-Second Elevator Pitch
> "A 100% deterministic decision support MVP built with FastAPI, React, and PostgreSQL that evaluates therapeutic drug substitutions against 9 sequential clinical safety checks and provides auditable pharmacist review workflows."

### 30-Second Elevator Pitch
> "Medication brand shortages frequently require pharmacy substitutions, but manual evaluation risks overlooking patient allergies, organ function limits, or drug interactions. Our system automates substitution safety evaluation through a deterministic 9-check pipeline and 5-tier candidate ranking algorithm. It enforces human-in-the-loop pharmacist reviews with mandatory override justifications, maintains immutable PostgreSQL audit logs, and monitors demographic fairness across patient cohorts."

### 1-Minute Elevator Pitch
> "Our Pharmacy Substitution Decision Support System addresses clinical safety and inventory challenges in hospital and retail settings. Built on FastAPI, SQLAlchemy, and React 18, it evaluates candidate drug alternatives against 9 sequential clinical safety rules—covering allergies, renal and hepatic function, pregnancy, age limits, drug interactions, dosage boundaries, and physical stock. Safe alternatives are ranked using a 5-tier deterministic algorithm. Every decision is persisted in PostgreSQL with an initial audit log. Licensed pharmacists can approve, reject, or clinically override safety blocks using token-authenticated endpoints and pessimistic row locking (`FOR UPDATE`). Governance dashboards provide real-time risk distributions, safety block root causes, and demographic cohort fairness metrics."

### 3-Minute Technical Deep-Dive
> "From an engineering perspective, the system prioritizes clinical safety, mathematical determinism, and auditability. Generative AI and non-deterministic LLMs were deliberately excluded because clinical decision support demands transparent, reproducible logic without hallucination risk.
> 
> The core engine executes 9 sequential safety checks: Approved Alternative Lookup, Allergy Contraindications, Renal Function Limits, Hepatic Impairment Limits, Pregnancy Contraindications, Age-Specific Boundaries, Drug-Drug Interactions, Maximum Daily Dosage, and Usable Inventory Stock. If any check fails, the candidate alternative is marked unsafe and excluded from recommendations.
> 
> When multiple alternatives pass, a 5-tier priority algorithm selects the best candidate: first, passing all 9 checks; second, lowest risk level (LOW < MEDIUM < HIGH < CRITICAL); third, highest usable unexpired stock; fourth, alphabetical ordering; and fifth, primary key tie-breaking.
> 
> Persistence and concurrency are hardened using SQLAlchemy and PostgreSQL (`pharmacy_substitution_db`). Decision evaluations and initial audit logs are written inside atomic single-transaction blocks. Pharmacist review submissions use `SELECT ... FOR UPDATE` row locking to prevent race conditions during concurrent override attempts. Custom middleware attaches `X-Request-ID` correlation UUIDs to all responses and sanitizes log output to prevent credential or traceback leaks. The React 18 frontend presents an intuitive, responsive dashboard displaying full check evidence, review history, audit trails, and demographic cohort fairness analysis."

---

## 35 Comprehensive Viva Defense Questions & Answers

### 1. What problem does this project solve?
**Answer**: It automates the clinical safety evaluation of therapeutic drug substitutions in pharmacy settings, preventing adverse drug events caused by overlooked patient allergies, organ impairments, drug interactions, pregnancy contraindications, or dosage boundary errors during medication brand/formulation changes.

### 2. Why pharmacy substitution?
**Answer**: Drug shortages, formulation discontinuations, and hospital formulary changes frequently require substituting prescribed medications. Manual substitution under time pressure leads to clinical errors, while automated decision support ensures zero unsafe substitutions are recommended.

### 3. What is the overall system architecture?
**Answer**: A decoupled full-stack architecture comprising a React 18 + Vite SPA frontend, a FastAPI REST API service layer in Python, SQLAlchemy ORM repositories, and a PostgreSQL database (`pharmacy_substitution_db`).

### 4. Why FastAPI instead of Django or Flask?
**Answer**: FastAPI provides automatic OpenAPI documentation generation, high performance via ASGI/Starlette, native Pydantic v2 data validation, and asynchronous execution capabilities ideal for REST APIs.

### 5. Why React for the frontend?
**Answer**: React 18 provides component-based UI architecture, efficient Virtual DOM state updates, and seamless integration with React Router v6 for managing single-page application views.

### 6. Why PostgreSQL instead of SQLite or MongoDB?
**Answer**: PostgreSQL provides robust ACID transaction guarantees, advanced pessimistic row locking (`SELECT FOR UPDATE`), foreign key constraint enforcement, superior concurrency handling, and enterprise production readiness required for medical audit trails.

### 7. Why SQLAlchemy ORM?
**Answer**: SQLAlchemy provides high-level Pythonic entity abstractions while giving explicit control over database transactions, session scopes, index definitions, and row locking primitives.

### 8. Why deterministic rules instead of machine learning or AI?
**Answer**: Clinical safety requires 100% reproducible, verifiable, and auditable decisions. Machine learning and LLMs introduce non-deterministic hallucinations, probabilistic errors, and black-box opacity that are unsuited for safety-critical clinical decisions.

### 9. Why isn't an LLM used for final clinical decisions?
**Answer**: LLMs cannot guarantee strict execution order, mathematical boundary enforcement, zero hallucination rates, or legal auditability required for clinical drug safety decisions.

### 10. Explain the 9 safety checks in detail.
**Answer**:
1. `approved_alternative`: Checks therapeutic category approval.
2. `allergy`: Matches active ingredients against patient allergen records.
3. `renal`: Compares patient eGFR against minimum renal safety thresholds.
4. `hepatic`: Evaluates hepatic impairment contraindication flags.
5. `pregnancy`: Checks teratogenic contraindications during pregnancy.
6. `age`: Validates patient age against pediatric and geriatric bounds.
7. `drug_interaction`: Compares alternative against co-prescribed medications.
8. `dosage`: Verifies maximum daily dose limit (mg/day).
9. `stock`: Checks physical unexpired stock in pharmacy inventory.

### 11. Why is the order of safety checks important?
**Answer**: Evaluating fundamental clinical contraindications (allergies, organ failure, pregnancy) before operational constraints (stock availability) ensures clinical reasons for blocking are prioritized and short-circuited efficiently.

### 12. Explain the 5-tier candidate ranking algorithm.
**Answer**:
1. Candidate passes all 9 safety checks (`is_safe == True`).
2. Lower risk level (`LOW` < `MEDIUM` < `HIGH` < `CRITICAL`).
3. Greater usable physical stock quantity.
4. Alphabetical medicine name ordering.
5. `MedicineAlternative.id` ascending tie-breaker.

### 13. How do you prevent unsafe recommendations?
**Answer**: If any safety check returns `FAIL`, the candidate alternative is marked `is_safe = False` and excluded from being selected as a `RECOMMENDED` drug.

### 14. How is allergy checking implemented?
**Answer**: The active ingredient of the candidate drug is normalized and compared against the patient's recorded allergen list in the `allergies` database table. Any match triggers a `FAIL`.

### 15. How is age checking implemented?
**Answer**: The patient's age in years is evaluated against `min_age` and `max_age` constraints in `clinical_constraints`.

### 16. How is drug interaction checking implemented?
**Answer**: Co-prescribed active ingredients from the patient's active prescriptions are checked against the comma-separated `interacting_drugs` field in `clinical_constraints`.

### 17. How is dosage checking implemented?
**Answer**: Prescribed dose multiplied by frequency per day is compared against `max_daily_dose_mg` in `medicine_alternatives`.

### 18. How is stock checking implemented?
**Answer**: Physical inventory stock is queried from `medicine_stocks`. If `usable_stock <= 0` or stock is expired, the check returns `FAIL`.

### 19. How does decision persistence work?
**Answer**: Evaluation results, individual check statuses, risk levels, and confidence scores are serialized and saved to `substitution_decisions` in PostgreSQL.

### 20. How does transaction rollback work?
**Answer**: If initial `AuditLog` creation fails during decision evaluation, SQLAlchemy catches the exception, executes `db.rollback()`, and raises an HTTP error, ensuring no orphaned decision records exist.

### 21. Why use `SELECT FOR UPDATE` in review submissions?
**Answer**: `SELECT FOR UPDATE` locks the target decision row in PostgreSQL, preventing concurrent review requests from overwriting decision status simultaneously.

### 22. How does audit logging work?
**Answer**: Every evaluation and review action appends an immutable row to `audit_logs` detailing the action, actor code, previous status, new status, timestamp, and audit reason.

### 23. How does the pharmacist review workflow work?
**Answer**: Pharmacists review persisted decisions and submit `APPROVED`, `REJECTED`, or `OVERRIDDEN` actions with their code and authorization header.

### 24. Why is `override_reason` mandatory for clinical overrides?
**Answer**: Overriding a clinical safety block is a high-risk action requiring legal accountability and documented clinical justification (e.g., specialist approval).

### 25. How does `X-Pharmacist-Token` work?
**Answer**: A prototype authorization header guard `get_authenticated_pharmacist` inspects incoming HTTP headers and rejects unauthorized review requests with `401 UNAUTHORIZED`.

### 26. What is `X-Request-ID`?
**Answer**: A unique correlation UUID generated or preserved by middleware for every HTTP request/response cycle, enabling request tracing across system logs.

### 27. How are error messages sanitized?
**Answer**: Global exception handlers intercept unhandled errors and return generic HTTP 500 error responses, suppressing database connection strings, passwords, SQL queries, and stack traces.

### 28. How does the demographic fairness endpoint work?
**Answer**: `GET /analytics/fairness` groups historical decisions into Age, Gender, and Organ Impairment cohorts, computing block rates and override counts for equity auditing.

### 29. What are the limitations of the fairness metrics?
**Answer**: Metrics are computed on synthetic population seed data for academic evaluation purposes and must be validated on real clinical datasets prior to production deployment.

### 30. What are the current project limitations?
**Answer**: Prototype header token authentication, reliance on synthetic clinical datasets, and lack of direct HL7/FHIR EHR integration.

### 31. How would you productionize authentication?
**Answer**: Replace prototype header token validation with OAuth2 / OpenID Connect (OIDC) using signed JWT tokens and Role-Based Access Control (RBAC).

### 32. How would you deploy this system to production?
**Answer**: Containerize backend and frontend services using Docker, deploy behind an Nginx reverse proxy with SSL/TLS termination, and host database on managed PostgreSQL (e.g., AWS RDS).

### 33. How would you scale PostgreSQL?
**Answer**: Implement database connection pooling (e.g., PgBouncer), read replicas for analytics queries, and index optimization on high-cardinality foreign key columns.

### 34. How would you add real clinical data safely?
**Answer**: Integrate standardized terminology systems (RxNorm, SNOMED CT, ICD-10) and establish secure HL7 FHIR API integrations with EHR systems.

### 35. How would you validate clinical rules before production deployment?
**Answer**: Conduct clinical validation trials with licensed hospital pharmacists, cross-referencing system recommendations against established clinical pharmacology reference databases (e.g., Lexicomp, Micromedex).
