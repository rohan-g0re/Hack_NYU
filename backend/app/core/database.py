"""
Database utilities and connection management.

WHAT: SQLite database setup with sync SQLAlchemy
WHY: Store negotiation state, agent data, session history with WAL mode for concurrency
HOW: Sync SQLAlchemy engine with WAL pragma and session management
"""

from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Base for models
Base = declarative_base()

# Create sync engine with proper SQLite configuration
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Use StaticPool for SQLite to avoid threading issues
    echo=settings.DEBUG
)


# Enable WAL mode for better concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    Set SQLite pragmas on connection.
    
    WHAT: Enable WAL mode and optimize SQLite settings
    WHY: Better concurrency and performance
    HOW: Execute PRAGMA statements on each connection
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
    logger.debug("SQLite pragmas set: WAL mode enabled, foreign keys ON")


# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


@contextmanager
def get_db():
    """
    Context manager for database sessions.
    
    WHAT: Provide database session with automatic cleanup
    WHY: Ensure sessions are properly closed
    HOW: Context manager pattern with try/finally
    
    Yields:
        Session: SQLAlchemy session
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


async def ping_database() -> dict:
    """
    Check database connectivity.
    
    WHAT: Test database connection
    WHY: Health check endpoint needs to verify DB availability
    HOW: Execute simple query and catch exceptions
    
    Returns:
        Dict with status and info
    """
    try:
        with get_db() as session:
            result = session.execute(text("SELECT 1"))
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
    """
    Initialize database tables.
    
    WHAT: Create all tables defined in models
    WHY: Setup database schema on first run
    HOW: Call create_all on metadata
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def close_db():
    """
    Close database connections.
    
    WHAT: Dispose of connection pool
    WHY: Clean shutdown
    HOW: Call engine.dispose()
    """
    engine.dispose()
    logger.info("Database connections closed")

