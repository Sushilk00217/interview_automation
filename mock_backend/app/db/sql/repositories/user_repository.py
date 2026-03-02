import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.sql.repositories.base import BaseRepository
from app.db.sql.models.user import User

class UserRepository(BaseRepository[User]):
    def __init__(self, session):
        super().__init__(session, User)

    async def get_by_id(self, id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == id).options(
            selectinload(User.admin_profile),
            selectinload(User.candidate_profile)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
        
    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email).options(
            selectinload(User.admin_profile),
            selectinload(User.candidate_profile)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
        
    async def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username).options(
            selectinload(User.admin_profile),
            selectinload(User.candidate_profile)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def create_user(self, user: User) -> User:
        self.add(user)
        return user

    async def update_user(self, user: User) -> User:
        # Changes are implicitly tracked by SQLAlchemy session
        return user

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        stmt = select(User).options(
            selectinload(User.admin_profile),
            selectinload(User.candidate_profile)
        ).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_candidate_profile(self, user_id: uuid.UUID) -> Optional["CandidateProfile"]:
        """Get candidate profile for a user."""
        from app.db.sql.models.user import CandidateProfile
        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()