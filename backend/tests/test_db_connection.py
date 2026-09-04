from app.db.session import check_db_connection, engine
from sqlalchemy import text


def test_postgres_connection():
    """Verify that PostgreSQL responds successfully to SELECT 1."""
    assert check_db_connection() is True


def test_raw_select_one_query():
    """Verify executing SELECT 1 directly via SQLAlchemy engine connection."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1
