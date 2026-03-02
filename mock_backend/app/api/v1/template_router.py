import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth_router import get_current_admin
from app.db.sql.session import get_db_session
from app.db.sql.models.user import User
from app.services.interview_admin_sql_service import InterviewAdminSQLService
from app.services.template_engine import generate_questions_from_template

router = APIRouter()

@router.get(
    "/",
    summary="List active interview templates",
    description="Admin-only. Returns all interview templates with is_active=True.",
)
async def list_templates(
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    return await InterviewAdminSQLService.list_active_templates(session)

@router.get(
    "/{template_id}/generate-preview",
    summary="Generate question preview from template",
    description="Admin-only. Logic-based sampling without persisting.",
)
async def generate_preview(
    template_id: str,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        t_id = uuid.UUID(template_id)
        questions = await generate_questions_from_template(session, t_id)
        
        return [
            {
                "question_id": str(q.id),
                "question_text": q.text,
                "category": q.category,
                "difficulty": q.difficulty,
                "order": i,
                "time_limit_sec": 120 # Default or from template if extended later
            }
            for i, q in enumerate(questions)
        ]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
