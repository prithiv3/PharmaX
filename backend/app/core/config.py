from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve absolute path to backend/.env
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Pharmacy Substitution Decision Support System"
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/pharmacy_substitution_db"
    )

    # ------------------------------------------------------------------
    # Capacity & Scheduling Constraints
    # ------------------------------------------------------------------
    # Maximum number of concurrent substitution evaluations the service
    # will accept before returning HTTP 429 Too Many Requests.
    MAX_CONCURRENT_EVALUATIONS: int = 50

    # Per-pharmacist review submission rate cap (requests per minute).
    # Enforcement is handled by CapacityGuard middleware.
    PHARMACIST_REVIEW_RATE_LIMIT_PER_MINUTE: int = 30

    # SQLAlchemy connection pool bounds – controls DB connection budget.
    DB_POOL_SIZE: int = 10          # base connections kept alive
    DB_MAX_OVERFLOW: int = 5        # extra connections allowed under burst
    DB_POOL_TIMEOUT_SECONDS: int = 10  # seconds to wait for a free slot
    DB_POOL_RECYCLE_SECONDS: int = 1800  # max connection lifetime

    # Maximum seconds allowed for a single evaluation pipeline run.
    # If the pipeline cannot complete within this window, a graceful
    # DEGRADED response is returned instead of a hard 500 error.
    EVALUATION_TIMEOUT_SECONDS: int = 15

    # ------------------------------------------------------------------
    # Graceful Fallback / Degradation Flags
    # ------------------------------------------------------------------
    # When True, the /ready endpoint failure causes evaluations to return
    # a synthetic DEGRADED decision rather than propagating a 503 error.
    ENABLE_GRACEFUL_DB_FALLBACK: bool = True

    # When True, the analytics/fairness endpoint returns a cached stub
    # response if the DB is unavailable, rather than raising 503.
    ENABLE_ANALYTICS_CACHE_FALLBACK: bool = True

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
