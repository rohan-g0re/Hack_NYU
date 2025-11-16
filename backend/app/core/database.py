"""
Database utilities and connection management.

WHAT: SQLite database setup and health checks
WHY: Store negotiation state, agent data, session history
HOW: SQLAlchemy async engine with health check method
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from .config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Convert sqlite:/// to sqlite+aiosqlite:///
DATABASE_URL = settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base for models
Base = declarative_base()


async def get_db():
    """
    Dependency for FastAPI endpoints to get database session.
    
    Yields:
        AsyncSession
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def ping_database() -> dict:
    """
    Check database connectivity.
    
    Returns:
        Dict with status and info
    """
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
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


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def close_db():
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")

