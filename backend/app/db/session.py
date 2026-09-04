from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create SQLAlchemy engine with connection pool pre-ping
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# Session factory for DB operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """FastAPI dependency for managing database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Utility function to test PostgreSQL connection by executing SELECT 1."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        scalar = result.scalar()
        return scalar == 1
