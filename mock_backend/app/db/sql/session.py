import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for injecting SQLAlchemy AsyncSession.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"SQL Session rollback due to exception: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

# Alias for backward compatibility with existing project routers
get_db = get_db_session

async def test_database_connection():
    """
    Test the connection to the database. Exits the app if connection fails.
    """
    import sys
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Successfully established connection to the database.")
    except Exception as e:
        logger.critical(f"Failed to connect to the database: {e}")
        sys.exit(1)
