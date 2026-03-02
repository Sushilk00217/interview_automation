import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.sql.unit_of_work import UnitOfWork
from app.db.sql.enums import InterviewStatus, UserRole
from app.db.sql.models.interview import Interview
from app.db.sql.models.interview_template import InterviewTemplate
from app.services.question_generator_service import question_generator_service

class InterviewAdminSQLService:
    @staticmethod
    def _assert_future_datetime(dt: datetime) -> None:
        """Raise 400 if dt is more than 10 minutes in the past (UTC)."""
        now_utc = datetime.now(timezone.utc)
        dt_aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        grace = timedelta(minutes=10)
        if dt_aware < now_utc - grace:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scheduled_at must not be more than 10 minutes in the past (UTC)",
            )

    @staticmethod
    async def create_interview(session: AsyncSession, template_id: uuid.UUID, candidate_id: uuid.UUID, assigned_by: uuid.UUID, scheduled_at: datetime) -> Interview:
        async with UnitOfWork(session) as uow:
            # 1. Validate candidate
            candidate = await uow.users.get_by_id(candidate_id)
            if not candidate:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
            if candidate.role != UserRole.CANDIDATE:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a candidate")
            if not candidate.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate account is inactive")
                
            # 2. Check active interview limits
            active = await uow.interviews.get_active_or_inprogress_for_candidate(candidate_id)
            if active:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate already has an active interview (status: scheduled or in_progress)")

            # 3. Validate template (Not in uow natively, so using session directly within transaction)
            result = await session.execute(select(InterviewTemplate).where(InterviewTemplate.id == template_id))
            template = result.scalar_one_or_none()
            if not template:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview template not found")
            if not template.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview template is not active")

            # 4. Validate time
            InterviewAdminSQLService._assert_future_datetime(scheduled_at)

            # 5. Build questions using resume and JD
            resume_id = None
            resume_text = None
            job_description = None
            if candidate.candidate_profile:
                resume_id = candidate.candidate_profile.resume_id
                resume_text = getattr(candidate.candidate_profile, "resume_text", None) or ""
                job_description = getattr(candidate.candidate_profile, "job_description", None) or ""

            curated_questions = question_generator_service.generate_curated_questions(
                template_id=str(template_id),
                candidate_id=str(candidate_id),
                resume_id=resume_id,
                resume_text=resume_text,
                job_description=job_description,
            )

            interview = Interview(
                candidate_id=candidate_id,
                template_id=template_id,
                assigned_by=assigned_by,
                status=InterviewStatus.SCHEDULED,
                scheduled_at=scheduled_at,
                curated_questions=curated_questions,
            )
            
            uow.interviews.create_interview(interview)
            await uow.flush()
            
            return interview

    @staticmethod
    async def list_all_interviews(session: AsyncSession) -> List[Interview]:
        async with UnitOfWork(session) as uow:
            result = await session.execute(select(Interview).order_by(Interview.created_at.desc()))
            return list(result.scalars().all())

    @staticmethod
    async def get_interview_details(session: AsyncSession, interview_id: uuid.UUID) -> Optional[Interview]:
        async with UnitOfWork(session) as uow:
            return await uow.interviews.get_by_id(interview_id)

    @staticmethod
    async def cancel_interview(session: AsyncSession, interview_id: uuid.UUID, reason: Optional[str] = None) -> Interview:
        async with UnitOfWork(session) as uow:
            interview = await uow.interviews.get_by_id(interview_id, with_for_update=True)
            if not interview:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
            if interview.status == InterviewStatus.COMPLETED:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed interviews cannot be cancelled")
            
            interview.status = InterviewStatus.CANCELLED
            interview.cancelled_at = datetime.now(timezone.utc)
            if reason:
                interview.cancellation_reason = reason
                
            return interview

    @staticmethod
    async def reschedule_interview(session: AsyncSession, interview_id: uuid.UUID, scheduled_at: datetime) -> Interview:
        async with UnitOfWork(session) as uow:
            interview = await uow.interviews.get_by_id(interview_id, with_for_update=True)
            if not interview:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
            if interview.status != InterviewStatus.SCHEDULED:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only scheduled interviews can be rescheduled")

            InterviewAdminSQLService._assert_future_datetime(scheduled_at)

            interview.scheduled_at = scheduled_at
            return interview

    @staticmethod
    async def get_interview_summary(session: AsyncSession, limit: int = 10, offset: int = 0, search: str = "") -> Dict[str, Any]:
        async with UnitOfWork(session) as uow:
            return await uow.interviews.get_all_summary(limit=limit, offset=offset, search=search)

    @staticmethod
    async def apply_template_to_interview(session: AsyncSession, interview_id: uuid.UUID, questions: List[Dict[str, Any]]) -> List[Any]:
        async with UnitOfWork(session) as uow:
            # 1. Fetch interview
            interview = await uow.interviews.get_by_id(interview_id)
            if not interview:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
            
            # 2. Clear existing session questions if any
            interview.session_questions = []
            
            # 3. Insert new questions
            from app.db.sql.models.interview import InterviewSessionQuestion
            
            for idx, q_data in enumerate(questions):
                q_id_str = q_data.get("question_id")
                sq = InterviewSessionQuestion(
                    interview_id=interview_id,
                    question_id=uuid.UUID(q_id_str) if q_id_str else None,
                    question_text=q_data["question_text"],
                    order=idx,
                    time_limit_sec=q_data["time_limit_sec"]
                )
                interview.session_questions.append(sq)
            
            await uow.flush()
            return interview.session_questions

    @staticmethod
    async def list_active_templates(session: AsyncSession) -> List[Dict[str, Any]]:
        result = await session.execute(select(InterviewTemplate).where(InterviewTemplate.is_active == True))
        templates = result.scalars().all()
        return [
            {
                "id": str(t.id),
                "name": t.title,                                               # title → name (frontend contract)
                "description": t.description,
                "total_duration_sec": (t.settings or {}).get("total_duration_sec", 3600),
                "is_active": t.is_active,
            }
            for t in templates
        ]
