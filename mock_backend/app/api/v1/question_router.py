from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.v1.auth_router import get_current_admin
from app.db.sql.session import get_db_session
from app.db.sql.models.user import User
from app.db.sql.models.question import Question

router = APIRouter()

@router.get(
    "/",
    summary="List all questions in the bank",
    description="Admin-only. Returns all active questions.",
)
async def list_questions(
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(Question).where(Question.is_active == True))
    questions = result.scalars().all()
    return [
        {
            "id": str(q.id),
            "text": q.text,
            "category": q.category,
            "difficulty": q.difficulty,
            "tags": q.tags
        }
        for q in questions
    ]
