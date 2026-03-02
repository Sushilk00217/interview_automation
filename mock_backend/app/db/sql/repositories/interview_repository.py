import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.sql.repositories.base import BaseRepository
from app.db.sql.models.interview import Interview
from app.db.sql.models.interview_session import InterviewSession
from app.db.sql.enums import InterviewStatus

class InterviewRepository(BaseRepository[Interview]):
    def __init__(self, session):
        super().__init__(session, Interview)

    def create_interview(self, interview: Interview) -> Interview:
        self.add(interview)
        return interview

    async def get_by_id(self, id: uuid.UUID, with_for_update: bool = False) -> Optional[Interview]:
        stmt = select(Interview).where(Interview.id == id).options(
            selectinload(Interview.sessions)
        )
        if with_for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_candidate(self, candidate_id: uuid.UUID) -> List[Interview]:
        stmt = select(Interview).where(Interview.candidate_id == candidate_id).order_by(Interview.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, id: uuid.UUID, status: InterviewStatus) -> Optional[Interview]:
        interview = await self.get_by_id(id)
        if interview:
            interview.status = status
        return interview

    def create_session(self, session_obj: InterviewSession) -> InterviewSession:
        self.session.add(session_obj)
        return session_obj

    async def get_active_or_inprogress_for_candidate(self, candidate_id: uuid.UUID) -> Optional[Interview]:
        stmt = select(Interview).where(
            Interview.candidate_id == candidate_id,
            Interview.status.in_([InterviewStatus.SCHEDULED, InterviewStatus.IN_PROGRESS])
        ).options(selectinload(Interview.sessions))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_summary(self, limit: int = 10, offset: int = 0, search: str = "") -> dict:
        from sqlalchemy import func, or_
        from app.db.sql.models.user import User, CandidateProfile
        
        stmt = select(
            Interview.id,
            Interview.candidate_id,
            Interview.status,
            Interview.scheduled_at,
            Interview.overall_score,
        )
        count_stmt = select(func.count(Interview.id))
        
        if search:
            search_term = f"%{search}%"
            join_cond = Interview.candidate_id == User.id
            filters = or_(
                CandidateProfile.first_name.ilike(search_term),
                CandidateProfile.last_name.ilike(search_term),
            )
            
            stmt = stmt.outerjoin(User, join_cond).outerjoin(CandidateProfile, User.id == CandidateProfile.user_id).where(filters)
            count_stmt = count_stmt.outerjoin(User, join_cond).outerjoin(CandidateProfile, User.id == CandidateProfile.user_id).where(filters)
            
        stmt = stmt.order_by(Interview.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.session.execute(stmt)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0
        
        data = [
            {
                "interview_id": row.id,
                "candidate_id": row.candidate_id,
                "status": row.status,
                "scheduled_at": row.scheduled_at,
                "overall_score": row.overall_score,
            }
            for row in result.all()
        ]
        
        return {
            "data": data,
            "total": total
        }
