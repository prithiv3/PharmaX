# Backend - Pharmacy Substitution Decision Support API

Minimal FastAPI backend for the Pharmacy Substitution Decision Support System.

## Architecture
- `app/main.py`: Entry point with CORS middleware and core health check endpoints.
- `app/core/`: Application settings and core configurations.
- `app/models/`: Internal data models.
- `app/schemas/`: Pydantic request and response schemas.
- `app/api/`: API routes and router definitions.
- `app/services/`: Business logic services.
- `app/rules/`: Clinical and substitution decision rules (to be implemented in future phase).
- `app/analytics/`: Evaluation metrics and analytics (to be implemented in future phase).

## Setup & Running
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
3. Run tests:
   ```bash
   pytest
   ```
