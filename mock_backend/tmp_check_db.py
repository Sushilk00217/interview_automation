import asyncio
from sqlalchemy import text
from app.db.sql.session import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = res.fetchall()
        print(f"Tables: {[t[0] for t in tables]}")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
