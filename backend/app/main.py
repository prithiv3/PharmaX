import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.substitutions import router as substitutions_router
from app.core.middleware import RequestCorrelationMiddleware
from app.db.session import check_db_connection

logger = logging.getLogger("app.main")

tags_metadata = [
    {
        "name": "System & Health",
        "description": "System status, health check, and database readiness endpoints.",
    },
    {
        "name": "Substitutions",
        "description": "Deterministic substitution decision engine evaluation, persistence, query, and pharmacist review endpoints.",
    },
    {
        "name": "Analytics & Governance",
        "description": "Dashboard analytics, demographic cohort fairness, and safety audit error analysis endpoints.",
    },
]

app = FastAPI(
    title="Pharmacy Substitution Decision Support API",
    description=(
        "Production-ready academic decision support system providing deterministic drug substitution evaluation, "
        "human-in-the-loop pharmacist review workflows, audit trails, demographic fairness analysis, and decision governance. "
        "\n\n**Security Notice**: Pharmacist review endpoints (`POST /api/v1/substitutions/{id}/review`) require prototype authorization header `X-Pharmacist-Token`."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# Register request correlation tracing middleware
app.add_middleware(RequestCorrelationMiddleware)

# Basic CORS configuration for React frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from Vite dev server and local origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(substitutions_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler ensuring internal exceptions return safe HTTP 500 error messages."""
    req_id = getattr(request.state, "request_id", "N/A")
    logger.error(f"Unhandled exception on request {req_id}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
        headers={"X-Request-ID": req_id},
    )


@app.get("/", tags=["System & Health"], summary="Root status check")
def read_root():
    """Root application status check."""
    return {
        "message": "Pharmacy Substitution Decision Support API",
        "status": "running",
    }


@app.get("/health", tags=["System & Health"], summary="Basic health check")
def health_check():
    """Basic health check endpoint returning application status."""
    return {"status": "healthy"}


@app.get("/ready", tags=["System & Health"], summary="Database readiness check")
def readiness_check():
    """Check database connectivity (PostgreSQL SELECT 1). Returns 200 OK if ready, 503 if unavailable."""
    try:
        if check_db_connection():
            return {"status": "ready", "database": "connected"}
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Database service unavailable."},
            )
    except Exception as exc:
        logger.error(f"Readiness check failed: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Database service unavailable."},
        )
