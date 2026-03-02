import asyncio
import logging
import sys
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sql.session import engine, AsyncSessionLocal
from seeds.seed_admin import seed_admin
from seeds.seed_templates import seed_templates
from seeds.seed_questions import seed_question_bank

# Configure logging for standalone execution
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def run_all_seeds():
    """Execute all seeding logic in order."""
    logger.info("Starting database seeding process...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Admin seeding
            await seed_admin(session)
            
            # 2. Template seeding
            await seed_templates(session)
            
            # 3. Question bank seeding
            await seed_question_bank(session)
            
            # Commit all changes
            await session.commit()
            logger.info("Successfully completed all seeding tasks.")
            
        except Exception as e:
            logger.error(f"Seeding failed: {e}")
            await session.rollback()
            sys.exit(1)
        finally:
            await session.close()
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_all_seeds())
