import uuid
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

async def seed_admin(session: AsyncSession):
    """Seed admin user and profile if they don't exist."""
    logger.info("Seeding admin data...")
    
    admin_hashed_pw = get_password_hash("admin")
    
    # Seed admin user (idempotent with ON CONFLICT)
    # Note: Using execute on session for raw sql
    await session.execute(
        text("""
            INSERT INTO users (id, username, email, role, hashed_password, is_active, login_disabled)
            VALUES (:id, 'admin', 'admin@example.com', 'ADMIN', :pw, true, false)
            ON CONFLICT (username) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
        """),
        {"id": uuid.uuid4(), "pw": admin_hashed_pw},
    )

    # Look up the admin to get the ID (could be the one we just inserted or existing)
    result = await session.execute(
        text("SELECT id FROM users WHERE username = 'admin'")
    )
    admin_id = result.scalar()

    # Seed admin profile (idempotent with ON CONFLICT)
    await session.execute(
        text("""
            INSERT INTO admin_profiles (id, user_id, first_name, last_name, department, designation)
            VALUES (:id, :user_id, 'Admin', 'User', 'HR', 'Recruiter')
            ON CONFLICT (user_id) DO NOTHING
        """),
        {"id": uuid.uuid4(), "user_id": admin_id},
    )
    
    logger.info("[OK] Admin user seeded: admin / admin")
