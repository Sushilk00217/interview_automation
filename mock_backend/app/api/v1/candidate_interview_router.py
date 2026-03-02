"""
Candidate Interview Router (Refactored for SQLAlchemy)
--------------------------
Endpoints for candidates to view and start their assigned interviews.

GET  /active               – Returns scheduled/in_progress interview for the logged-in candidate
POST /{interview_id}/start – Creates or resumes an interview session (generates questions from resume+JD via LLM when starting).
"""

import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth_router import get_current_active_user
from app.db.sql.session import get_db_session
from app.db.sql.models.user import User
from app.db.sql.enums import UserRole
from app.services.interview_sql_service import InterviewSQLService

logger = logging.getLogger(__name__)
CANDIDATE_MATERIALS_COLLECTION = "candidate_materials"
router = APIRouter()

# ─── Candidate auth guard ─────────────────────────────────────────────────────

async def get_current_candidate(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can access this endpoint",
        )
    return current_user

# ─── GET /active ──────────────────────────────────────────────────────────────

@router.get(
    "/active",
    summary="Get the candidate's active or in-progress interview",
    description=(
        "Returns the scheduled or in_progress interview for the logged-in candidate. "
        "For in_progress interviews it also returns the active session_id so the candidate "
        "can rejoin. Returns null when no active interview exists."
    ),
)
async def get_active_interview(
    current_candidate: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
) -> Optional[Dict[str, Any]]:
    # ID is guaranteed by SQL to natively be UUID type on the ORM Model
    candidate_id = current_candidate.id
    return await InterviewSQLService.get_active_interview_for_candidate(session, candidate_id)

# ─── POST /{interview_id}/start ───────────────────────────────────────────────

@router.post(
    "/{interview_id}/start",
    summary="Start or rejoin an interview session",
    description=(
        "Validates the interview belongs to the candidate and is in 'scheduled' "
        "status with scheduled_at <= now. Creates a new session (or returns the "
        "existing one) and transitions the interview to 'in_progress'."
    ),
)
async def start_interview(
    interview_id: str,
    current_candidate: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    
    # Strictly validate string back to purely database-agnostic UUID identifier
    try:
        validated_interview_id = uuid.UUID(interview_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid interview_id UUID format: {interview_id}",
        )

    candidate_id = current_candidate.id
    return await InterviewSQLService.start_interview(session, validated_interview_id, candidate_id)
