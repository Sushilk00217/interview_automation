import asyncio
from sqlalchemy import text
from app.db.sql.session import AsyncSessionLocal

async def clear_alembic_version():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(text("DROP TABLE IF EXISTS alembic_version"))
            print("Dropped alembic_version table.")

if __name__ == "__main__":
    asyncio.run(clear_alembic_version())
