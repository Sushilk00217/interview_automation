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
from app.db.sql.models.interview_session_question import InterviewSessionQuestion
from app.services.question_generator_service import question_generator_service
from app.services.template_engine import template_engine

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
    async def create_interview(
        session: AsyncSession, 
        template_id: uuid.UUID, 
        candidate_id: uuid.UUID, 
        assigned_by: uuid.UUID, 
        scheduled_at: datetime,
        questions: Optional[List[Any]] = None,
        draft_interview_id: Optional[uuid.UUID] = None
    ) -> Interview:
        async with UnitOfWork(session) as uow:
            # If draft_interview_id is provided, we just update it
            if draft_interview_id:
                interview = await uow.interviews.get_by_id(draft_interview_id, with_for_update=True)
                if not interview:
                    raise HTTPException(status_code=404, detail="Draft interview not found")
                
                # Check if it belongs to the right candidate and template
                if interview.candidate_id != candidate_id or interview.template_id != template_id:
                    raise HTTPException(status_code=400, detail="Draft interview mismatch with candidate/template")
                
                # Update status and scheduled_at
                interview.status = InterviewStatus.SCHEDULED
                interview.scheduled_at = scheduled_at
                interview.assigned_by = assigned_by # Refresh assigned_by
                
                await uow.flush()
                return interview

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

            # 3. Validate template
            result = await session.execute(
                select(InterviewTemplate)
                .where(InterviewTemplate.id == template_id)
                .with_for_update()
            )
            template = result.scalar_one_or_none()
            if not template:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview template not found")
            
            # 4. Build curated questions
            # Reuse logic from generate_curated_questions
            profile = candidate.candidate_profile
            curated_questions = await question_generator_service.generate_curated_questions(
                session=session,
                template_id=str(template_id),
                candidate_id=str(candidate_id),
                resume_id=profile.resume_id if profile else None,
                resume_text=profile.resume_text if profile else "",
                job_description=profile.job_description if profile else "",
                resume_json=profile.resume_json if profile else None,
                jd_json=profile.jd_json if profile else None,
            )

            # 5. Create Interview record
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
    async def get_draft_interview(
        session: AsyncSession,
        template_id: uuid.UUID,
        candidate_id: uuid.UUID
    ) -> Optional[Interview]:
        """Find an existing draft interview for this template and candidate."""
        stmt = select(Interview).where(
            Interview.template_id == template_id,
            Interview.candidate_id == candidate_id,
            Interview.status == InterviewStatus.DRAFT
        ).order_by(Interview.created_at.desc())
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def create_draft_interview(
        session: AsyncSession,
        template_id: uuid.UUID,
        candidate_id: uuid.UUID,
        assigned_by: uuid.UUID,
        curated_questions: Dict[str, Any]
    ) -> Interview:
        """Create a new interview in DRAFT status."""
        interview = Interview(
            candidate_id=candidate_id,
            template_id=template_id,
            assigned_by=assigned_by,
            status=InterviewStatus.DRAFT,
            scheduled_at=datetime.utcnow() + timedelta(days=365), # Far future default
            curated_questions=curated_questions
        )
        session.add(interview)
        await session.flush()
        return interview

    @staticmethod
    async def regenerate_interview_question(
        session: AsyncSession,
        interview_id: uuid.UUID,
        question_id: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Regenerate a single question in a draft interview."""
        async with UnitOfWork(session) as uow:
            interview = await uow.interviews.get_by_id(interview_id, with_for_update=True)
            if not interview:
                raise HTTPException(status_code=404, detail="Interview not found")
            
            if interview.status != InterviewStatus.DRAFT:
                raise HTTPException(status_code=400, detail="Can only regenerate questions for DRAFT interviews")

            curated = interview.curated_questions or {}
            
            # Identify section
            section_type = None # 'technical' or 'coding'
            target_idx = -1
            target_q = None
            questions_list = []

            # 1. Search in technical_section
            tech_questions = (curated.get('technical_section') or {}).get('questions', [])
            if not tech_questions and 'questions' in curated: # Legacy flat structure
                tech_questions = curated.get('questions', [])
            
            for idx, q in enumerate(tech_questions):
                if q.get('question_id') == question_id:
                    section_type = 'technical'
                    target_idx = idx
                    target_q = q
                    questions_list = tech_questions
                    break
            
            # 2. Search in coding_section if not found
            if section_type is None:
                coding_problems = (curated.get('coding_section') or {}).get('problems', [])
                for idx, p in enumerate(coding_problems):
                    if p.get('problem_id') == question_id:
                        section_type = 'coding'
                        target_idx = idx
                        target_q = p
                        questions_list = coding_problems
                        break
            
            if section_type is None:
                raise HTTPException(status_code=404, detail="Question not found in interview")

            from app.services.question_generator_service import question_generator_service
            new_q = None
            
            if section_type == 'technical':
                # Determine regeneration strategy based on source
                source = target_q.get('source', 'llm_generated')
                template = await session.get(InterviewTemplate, interview.template_id)
                preferred_source = "ai_generated"
                if template and template.technical_config:
                    preferred_source = template.technical_config.get("question_source", "ai_generated")

                # Context
                candidate = await uow.users.get_by_id(interview.candidate_id)
                profile = candidate.candidate_profile if candidate else None
                skills = profile.skills if profile else []
                if profile and profile.resume_json:
                    skills = list(set(skills + (profile.resume_json.get('skills', []))))

                if source == "question_bank" and preferred_source == "question_bank":
                    exclude_ids = [q.get('question_id') for q in questions_list]
                    new_q = await question_generator_service._get_single_replacement_question_from_bank(
                        session=session,
                        exclude_ids=exclude_ids,
                        skills=skills,
                        difficulty=target_q.get('difficulty', 'medium')
                    )
                
                if not new_q:
                    new_q = await question_generator_service._regenerate_single_question_with_llm(
                        existing_question=target_q,
                        all_questions=questions_list,
                        comment=comment,
                        skills=skills,
                        resume_data=profile.resume_json if profile else None,
                        jd_data=profile.jd_json if profile else None
                    )
                
                if new_q:
                    new_q['order'] = target_q.get('order', target_idx + 1)
                    new_q['text'] = new_q.get('prompt')
                    questions_list[target_idx] = new_q
                    
                    if 'technical_section' not in interview.curated_questions:
                        interview.curated_questions['technical_section'] = {}
                    interview.curated_questions['technical_section']['questions'] = questions_list
            
            elif section_type == 'coding':
                # Coding problem regeneration (refetch from bank)
                template = await session.get(InterviewTemplate, interview.template_id)
                config = template.coding_config or {}
                difficulties = config.get("difficulty", ["medium"])
                
                exclude_ids = [p.get('problem_id') for p in questions_list]
                new_q = await question_generator_service._get_single_replacement_coding_problem_from_bank(
                    session=session,
                    exclude_ids=exclude_ids,
                    difficulties=difficulties
                )
                
                if new_q:
                    questions_list[target_idx] = new_q
                    if 'coding_section' not in interview.curated_questions:
                        interview.curated_questions['coding_section'] = {}
                    interview.curated_questions['coding_section']['problems'] = questions_list

            if new_q:
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(interview, "curated_questions")
                await session.commit() # PERSIST the regeneration
                return new_q
            
            raise HTTPException(status_code=500, detail="Failed to regenerate questions")


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
    async def list_active_templates(session: AsyncSession) -> List[Dict[str, Any]]:
        result = await session.execute(select(InterviewTemplate).where(InterviewTemplate.is_active == True))
        templates = result.scalars().all()
        return [
            {
                "id": str(t.id),
                "name": t.title,                                               # title → name (frontend contract)
                "title": t.title,
                "description": t.description,
                "total_duration_sec": (t.settings or {}).get("total_duration_sec", 3600),
                "is_active": t.is_active,
            }
            for t in templates
        ]
