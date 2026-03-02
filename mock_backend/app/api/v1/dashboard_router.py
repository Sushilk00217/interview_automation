from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from typing import Dict

from app.db.sql.session import get_db_session
from app.db.sql.models.interview import Interview
from app.db.sql.enums import InterviewStatus

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(session: AsyncSession = Depends(get_db_session)) -> Dict[str, int]:
    """
    Get dashboard statistics using real database aggregates.
    """
    result_total = await session.execute(select(func.count(Interview.id)))
    total_interviews = result_total.scalar() or 0

    result_completed = await session.execute(select(func.count(Interview.id)).where(Interview.status == InterviewStatus.COMPLETED))
    completed = result_completed.scalar() or 0

    result_pending = await session.execute(select(func.count(Interview.id)).where(Interview.status == InterviewStatus.PENDING_REVIEW))
    pending_review = result_pending.scalar() or 0

    result_candidates = await session.execute(select(func.count(distinct(Interview.candidate_id))))
    total_candidates = result_candidates.scalar() or 0

    return {
        "total_interviews": total_interviews,
        "completed": completed,
        "pending_review": pending_review,
        "total_candidates": total_candidates
    }
