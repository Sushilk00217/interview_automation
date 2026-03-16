import asyncio
import logging
from sqlalchemy import text
from app.db.sql.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

async def clear_alembic_version():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(text("DROP TABLE IF EXISTS alembic_version"))
            logger.info("Dropped alembic_version table.")

if __name__ == "__main__":
    asyncio.run(clear_alembic_version())
