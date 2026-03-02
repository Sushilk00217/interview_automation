"""
Interview Router — Admin-only scheduling endpoints (Refactored for SQLAlchemy)
----------------------------------------------------
POST   /admin/interviews/schedule          – Create a new scheduled interview
PUT    /admin/interviews/{id}/reschedule   – Move interview to a new datetime
PUT    /admin/interviews/{id}/cancel       – Cancel a non-completed interview
"""

import uuid
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.v1.auth_router import get_current_admin
from app.db.sql.session import get_db_session
from app.db.sql.models.user import User
from app.schemas.interview import (
    ScheduleInterviewRequest,
    ScheduleInterviewResponse,
    RescheduleInterviewRequest,
    RescheduleInterviewResponse,
    CancelInterviewRequest,
    CancelInterviewResponse,
    ApplyTemplateRequest,
)
from app.services.interview_admin_sql_service import InterviewAdminSQLService
from app.db.sql.enums import InterviewStatus

router = APIRouter()

def validate_uuid(id_str: str) -> uuid.UUID:
    try:
        return uuid.UUID(id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid UUID: {id_str}",
        )


@router.get(
    "/summary",
    summary="Get a lightweight summary of all interviews",
    description=(
        "Admin-only. Returns candidate_id, interview_id, status, and scheduled_at "
        "for every interview. Excludes curated_questions for performance."
    ),
)
async def get_interview_summary(
    limit: int = 10,
    offset: int = 0,
    search: str = "",
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    result = await InterviewAdminSQLService.get_interview_summary(session, limit, offset, search)
    data = [
        {
            "interview_id": str(s["interview_id"]),
            "candidate_id": str(s["candidate_id"]) if s["candidate_id"] else None,
            "status": s["status"].value if isinstance(s["status"], InterviewStatus) else s["status"],
            "scheduled_at": s["scheduled_at"],
            "overall_score": s.get("overall_score"),
        }
        for s in result["data"]
    ]
    return {
        "data": data,
        "total": result["total"],
        "limit": limit,
        "offset": offset
    }


@router.post(
    "/schedule",
    response_model=ScheduleInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a new interview for a candidate",
    description=(
        "Admin-only. Validates candidate eligibility, checks for existing "
        "active interviews, verifies template, and creates the interview document "
        "with a mock curated questions payload."
    ),
)
async def schedule_interview(
    request: ScheduleInterviewRequest,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    template_id = validate_uuid(request.template_id)
    candidate_id = validate_uuid(request.candidate_id)
    
    interview = await InterviewAdminSQLService.create_interview(
        session=session,
        template_id=template_id,
        candidate_id=candidate_id,
        assigned_by=current_admin.id,
        scheduled_at=request.scheduled_at,
    )
    
    return {
        "id": str(interview.id),
        "candidate_id": str(interview.candidate_id),
        "template_id": str(interview.template_id),
        "assigned_by": str(interview.assigned_by),
        "status": interview.status.value if isinstance(interview.status, InterviewStatus) else interview.status,
        "scheduled_at": interview.scheduled_at,
        "curated_questions": interview.curated_questions,
        "created_at": interview.created_at,
    }

@router.put(
    "/{interview_id}/reschedule",
    response_model=RescheduleInterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Reschedule an existing interview",
    description=(
        "Admin-only. Moves a 'scheduled' interview to a new future datetime. "
        "Returns 409 if status is anything other than 'scheduled'."
    ),
)
async def reschedule_interview(
    interview_id: str,
    request: RescheduleInterviewRequest,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    validated_id = validate_uuid(interview_id)
    interview = await InterviewAdminSQLService.reschedule_interview(
        session=session,
        interview_id=validated_id,
        scheduled_at=request.scheduled_at,
    )
    
    return {
        "id": str(interview.id),
        "status": interview.status.value if isinstance(interview.status, InterviewStatus) else interview.status,
        "scheduled_at": interview.scheduled_at,
        "updated_at": interview.updated_at,
    }


@router.put(
    "/{interview_id}/cancel",
    response_model=CancelInterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel an interview",
    description=(
        "Admin-only. Cancels an interview by setting status to 'cancelled'. "
        "The document is never deleted. Returns 409 if status is 'completed'."
    ),
)
async def cancel_interview(
    interview_id: str,
    request: CancelInterviewRequest = CancelInterviewRequest(),
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    validated_id = validate_uuid(interview_id)
    interview = await InterviewAdminSQLService.cancel_interview(
        session=session,
        interview_id=validated_id,
        reason=request.reason,
    )
    
    return {
        "id": str(interview.id),
        "status": interview.status.value if isinstance(interview.status, InterviewStatus) else interview.status,
        "cancelled_at": interview.cancelled_at,
        "reason": interview.cancellation_reason,
    }

@router.post(
    "/{interview_id}/apply-template",
    status_code=status.HTTP_200_OK,
    summary="Persist a template snapshot for an interview",
    description="Admin-only. Saves a immutable copy of questions to the interview session.",
)
async def apply_template(
    interview_id: str,
    request: ApplyTemplateRequest,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
):
    validated_id = validate_uuid(interview_id)
    # Convert Pydantic models to dicts for the service
    questions_data = [q.model_dump() for q in request.questions]
    
    saved_questions = await InterviewAdminSQLService.apply_template_to_interview(
        session=session,
        interview_id=validated_id,
        questions=questions_data
    )
    
    return {
        "interview_id": interview_id,
        "questions_count": len(saved_questions),
        "status": "applied"
    }
