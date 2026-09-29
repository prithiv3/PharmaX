import logging
from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings

logger = logging.getLogger("app.db.session")

# ---------------------------------------------------------------------------
# Engine – pool constraints sourced from Settings (capacity requirements)
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    # Health-check each connection before use – catches stale connections
    pool_pre_ping=True,
    # Capacity/scheduling constraints from Settings
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
    pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
)

# Session factory for DB operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Standard DB dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator:
    """FastAPI dependency for managing database sessions.

    Yields a SQLAlchemy Session and guarantees close() on exit.
    Connection-pool exhaustion (QueuePool overflow) propagates as a 503-level
    error and is handled by the global exception handler in main.py.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Graceful-fallback DB dependency
# ---------------------------------------------------------------------------

def get_db_with_fallback() -> Generator[Optional[Session], None, None]:
    """FastAPI dependency that yields None instead of raising if the DB is
    unreachable and ENABLE_GRACEFUL_DB_FALLBACK is True.

    API endpoints using this dependency MUST handle a None session by
    returning a synthetic degraded response (e.g. cached stub data or an
    informative 503 JSON body) rather than performing database operations.

    Usage:
        db: Optional[Session] = Depends(get_db_with_fallback)
        if db is None:
            return _degraded_response()
    """
    if not settings.ENABLE_GRACEFUL_DB_FALLBACK:
        # When fallback is disabled, behave identically to get_db()
        yield from get_db()
        return

    db: Optional[Session] = None
    try:
        db = SessionLocal()
        # Lightweight connectivity probe – fails fast on broken pool slot
        db.execute(text("SELECT 1"))
        yield db
    except (OperationalError, SQLAlchemyError) as exc:
        logger.warning(
            "Database unreachable; yielding None for graceful fallback. "
            f"Reason: {type(exc).__name__}"
        )
        if db is not None:
            try:
                db.close()
            except Exception:
                pass
        yield None
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Readiness probe
# ---------------------------------------------------------------------------

def check_db_connection() -> bool:
    """Utility function to test PostgreSQL connection by executing SELECT 1."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            scalar = result.scalar()
            return scalar == 1
    except (OperationalError, SQLAlchemyError) as exc:
        logger.warning(f"DB connection check failed: {type(exc).__name__}")
        return False
