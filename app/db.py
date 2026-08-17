"""
Sonic AI — Database Configuration
Supports PostgreSQL (production) and SQLite (development/Render free tier).
"""

import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import Base

logger = logging.getLogger(__name__)

# Detect database type from URL
is_sqlite = settings.database_url.startswith("sqlite")

# Create engine with appropriate settings
if is_sqlite:
    logger.info(f"Using SQLite database: {settings.database_url}")
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},  # SQLite specific
        echo=False,
    )

    # SQLite doesn't support connection pooling the same way
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety/performance
        cursor.close()
else:
    logger.info(f"Using PostgreSQL database")
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
