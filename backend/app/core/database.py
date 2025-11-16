"""
Database utilities and connection management.

WHAT: SQLite database setup with WAL mode for Phase 3
WHY: Store negotiation state, agent data, session history with Windows ARM compatibility
HOW: SQLAlchemy sync engine v2 with WAL mode, session management
"""

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from pathlib import Path

from .config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Ensure data directory exists
data_dir = Path(settings.DATABASE_URL.replace("sqlite:///", "")).parent
if not data_dir.exists():
    data_dir.mkdir(parents=True, exist_ok=True)

# Create sync engine (Windows ARM compatible, per spec)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Allow multi-threaded access
    echo=settings.DEBUG,
    future=True
)

# Enable WAL mode on connection
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode for better concurrency."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")  # Enable FK constraints
    cursor.close()

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Base for models
Base = declarative_base()


@contextmanager
def get_db():
    """
    Context manager for database session.
    
    Usage:
        with get_db() as db:
            # use db session
            pass
    
    Yields:
        Session: SQLAlchemy session
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping_database() -> dict:
    """
    Check database connectivity.
    
    Returns:
        Dict with status and info
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        return {
            "available": True,
            "url": settings.DATABASE_URL,
            "error": None
        }
    except Exception as e:
        logger.error(f"Database ping failed: {e}")
        return {
            "available": False,
            "url": settings.DATABASE_URL,
            "error": str(e)
        }


def init_db():
    """Initialize database tables and enable WAL mode."""
    with engine.connect() as conn:
        # Ensure WAL mode
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized with WAL mode")


def close_db():
    """Close database connections."""
    engine.dispose()
    logger.info("Database connections closed")
