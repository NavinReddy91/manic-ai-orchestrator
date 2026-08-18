"""
Manic AI — Database Configuration
Supports PostgreSQL (production) and SQLite (development/Render free tier).
Falls back to SQLite if PostgreSQL connection fails.
"""

import logging
import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import Base

logger = logging.getLogger(__name__)

# Global engine and session - will be initialized lazily
_engine = None
_SessionLocal = None
_db_initialized = False


def _create_sqlite_engine(db_url: str):
    """Create SQLite engine with optimizations."""
    logger.info(f"Using SQLite database: {db_url}")
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    return engine


def _create_postgres_engine(db_url: str):
    """Create PostgreSQL engine with SSL support for NeonDB."""
    # Check if psycopg2 is available
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        raise ImportError(
            "PostgreSQL driver (psycopg2) is not installed. "
            "Install it with 'pip install psycopg2-binary'"
        )

    # Handle SSL for NeonDB and other cloud PostgreSQL providers
    connect_args = {}
    if "sslmode=require" in db_url or "neon.tech" in db_url:
        # For NeonDB and similar providers that require SSL
        connect_args["sslmode"] = "require"
        logger.info("SSL enabled for PostgreSQL connection")

    logger.info("Using PostgreSQL database")
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
        connect_args=connect_args,
    )


def _get_engine():
    """Get or create the database engine."""
    global _engine

    if _engine is not None:
        return _engine

    db_url = settings.database_url

    # If explicitly SQLite, use it directly
    if db_url.startswith("sqlite"):
        _engine = _create_sqlite_engine(db_url)
        return _engine

    # PostgreSQL - fail loudly if connection fails (no silent fallback)
    # This ensures configuration issues are caught immediately
    try:
        engine = _create_postgres_engine(db_url)
        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("PostgreSQL connection successful")
        _engine = engine
        return _engine
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        logger.warning("Falling back to local SQLite database: sqlite:///./manic_ai.db")
        _engine = _create_sqlite_engine("sqlite:///./manic_ai.db")
        return _engine


def get_session_local():
    """Get the session factory, creating it if needed."""
    global _SessionLocal

    if _SessionLocal is None:
        engine = _get_engine()
        _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    return _SessionLocal


def init_db():
    """Create all tables. Called during app startup."""
    global _db_initialized

    if _db_initialized:
        return

    engine = _get_engine()
    SessionLocal = get_session_local()

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
        _db_initialized = True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        try:
            logger.warning("Retrying database initialization with SQLite fallback...")
            sqlite_engine = _create_sqlite_engine("sqlite:///./manic_ai.db")
            Base.metadata.create_all(bind=sqlite_engine)
            global _engine
            _engine = sqlite_engine
            _db_initialized = True
        except Exception as sq_err:
            logger.error(f"SQLite fallback initialization failed: {sq_err}")


def get_db():
    """FastAPI dependency for database sessions."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Backward compatibility: SessionLocal as a callable that returns a session
class _SessionLocalCompat:
    """
    Compatibility wrapper that mimics the old SessionLocal behavior.
    Call it like: db = SessionLocal()
    """

    def __call__(self):
        factory = get_session_local()
        return factory()


SessionLocal = _SessionLocalCompat()
