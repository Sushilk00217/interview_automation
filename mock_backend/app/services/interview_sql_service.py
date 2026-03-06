import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sql.unit_of_work import UnitOfWork
from app.db.sql.enums import InterviewStatus
from app.db.sql.models.interview_session import InterviewSession
from app.db.sql.models.interview_session_question import InterviewSessionQuestion
from app.db.sql.models.question import Question

class InterviewSQLService:
    @staticmethod
    async def get_active_interview_for_candidate(session: AsyncSession, candidate_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        async with UnitOfWork(session) as uow:
            # Replaces repo.get_active_or_inprogress_for_candidate
            interview = await uow.interviews.get_active_or_inprogress_for_candidate(candidate_id)
            if not interview:
                return None

            # Check if interview has expired (72 hours from scheduled_at)
            now_utc = datetime.now(timezone.utc)
            if interview.scheduled_at:
                expiration_time = interview.scheduled_at + timedelta(hours=72)
                if now_utc > expiration_time:
                    # Interview has expired, don't return it
                    return None

            interview_id = interview.id
            interview_status = interview.status

            if interview_status == InterviewStatus.SCHEDULED:
                scheduled_at = interview.scheduled_at
                time_ready = scheduled_at is not None and scheduled_at <= now_utc
                
                # Check verification status
                candidate = await uow.users.get_by_id(candidate_id)
                face_verified = False
                voice_verified = False
                if candidate and candidate.candidate_profile:
                    face_verified = candidate.candidate_profile.face_verified or False
                    voice_verified = candidate.candidate_profile.voice_verified or False
                
                verification_ready = face_verified and voice_verified
                can_start = time_ready and verification_ready
                
                # Format scheduled_at as ISO string if it exists
                scheduled_at_str = scheduled_at.isoformat() if scheduled_at else None
                
                return {
                    "interview_id": str(interview_id),
                    "session_id": None,
                    "status": interview_status.value,
                    "scheduled_at": scheduled_at_str,
                    "can_start": can_start,
                    "face_verified": face_verified,
                    "voice_verified": voice_verified,
                }

            if interview_status == InterviewStatus.IN_PROGRESS:
                # Get the active session if one exists
                active_session = next((s for s in interview.sessions if s.status == "active"), None)
                session_id = str(active_session.id) if active_session else None
                scheduled_at_str = interview.scheduled_at.isoformat() if interview.scheduled_at else None
                return {
                    "interview_id": str(interview_id),
                    "session_id": session_id,
                    "status": interview_status.value,
                    "scheduled_at": scheduled_at_str,
                    "can_start": True,
                    "face_verified": True,  # Already verified if in progress
                    "voice_verified": True,
                }
            
            return None

    @staticmethod
    async def start_interview(session: AsyncSession, interview_id: uuid.UUID, candidate_id: uuid.UUID) -> Dict[str, Any]:
        async with UnitOfWork(session) as uow:
            interview = await uow.interviews.get_by_id(interview_id, with_for_update=True)
            
            if not interview:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Interview not found"
                )

            # Ownership check
            if interview.candidate_id != candidate_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This interview does not belong to you"
                )

            current_status = interview.status

            # Idempotent rejoin if already in_progress
            if current_status == InterviewStatus.IN_PROGRESS:
                active_session = next((s for s in interview.sessions if s.status == "active"), None)
                return {
                    "session_id": str(active_session.id) if active_session else None,
                    "interview_id": str(interview_id),
                    "status": current_status.value,
                }

            if current_status != InterviewStatus.SCHEDULED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot start interview with status '{current_status.value}'"
                )

            # Time gate: scheduled_at must be <= now (UTC)
            if interview.scheduled_at:
                now_utc = datetime.now(timezone.utc)
                if interview.scheduled_at > now_utc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Interview cannot be started before the scheduled time"
                    )
            
            # Verification check: candidate must have uploaded face and voice samples
            candidate = await uow.users.get_by_id(candidate_id)
            if candidate and candidate.candidate_profile:
                if not candidate.candidate_profile.face_verified or not candidate.candidate_profile.voice_verified:
                    missing = []
                    if not candidate.candidate_profile.face_verified:
                        missing.append("face sample (photo)")
                    if not candidate.candidate_profile.voice_verified:
                        missing.append("voice sample")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Please upload and verify your {', '.join(missing)} before starting the interview"
                    )

            # Transition interview to in_progress
            interview.status = InterviewStatus.IN_PROGRESS
            now = datetime.now(timezone.utc)
            interview.started_at = now
            
            # Create a new session
            new_session = InterviewSession(
                interview_id=interview_id,
                candidate_id=candidate_id,
                started_at=now,
                status="active"
            )
            uow.interviews.create_session(new_session)
            await uow.flush() # Needed so we can return the ID and use it for relationships
            
            # Retrieve durations from template configs
            tech_dur = 20
            coding_dur = 40
            conv_dur = 15
            
            from app.db.sql.models.interview_template import InterviewTemplate
            template_obj = None
            if interview.template_id:
                template_obj = await uow.session.get(InterviewTemplate, interview.template_id)
                
            if template_obj:
                t_cfg = template_obj.technical_config or {}
                c_cfg = template_obj.coding_config or {}
                v_cfg = template_obj.conversational_config or {}
                
                # Tech duration
                if "duration_minutes" in t_cfg and t_cfg["duration_minutes"] > 0:
                    tech_dur = t_cfg["duration_minutes"]
                else:
                    logger.warning(f"Interview {interview_id}: Missing technical duration in template {template_obj.id}, using default 20m")
                
                # Coding duration
                if "duration_minutes" in c_cfg and c_cfg["duration_minutes"] > 0:
                    coding_dur = c_cfg["duration_minutes"]
                else:
                    logger.warning(f"Interview {interview_id}: Missing coding duration in template {template_obj.id}, using default 40m")
                
                # Conversational duration
                if "duration_minutes" in v_cfg and v_cfg["duration_minutes"] > 0:
                    conv_dur = v_cfg["duration_minutes"]
                else:
                    logger.warning(f"Interview {interview_id}: Missing conversational duration in template {template_obj.id}, using default 15m")
            else:
                logger.warning(f"Interview {interview_id}: No template found for session creation, using global defaults for durations")

            from app.db.sql.models.interview_session_section import InterviewSessionSection
            
            # Create the three sections with extracted durations
            tech_section = InterviewSessionSection(
                interview_session_id=new_session.id,
                section_type="technical",
                order_index=1,
                duration_minutes=tech_dur,
                status="pending"
            )
            coding_section = InterviewSessionSection(
                interview_session_id=new_session.id,
                section_type="coding",
                order_index=2,
                duration_minutes=coding_dur,
                status="pending"
            )
            conv_section = InterviewSessionSection(
                interview_session_id=new_session.id,
                section_type="conversational",
                order_index=3,
                duration_minutes=conv_dur,
                status="pending"
            )
            uow.session.add_all([tech_section, coding_section, conv_section])
            await uow.flush()
            
            section_map = {
                "technical": tech_section.id,
                "coding": coding_section.id,
                "conversational": conv_section.id
            }

            from app.db.sql.models.interview_session_question import InterviewSessionQuestion
            from app.db.sql.models.question import Question

            order_idx = 1
            
            # 1. ADD TECHNICAL AND CONVERSATIONAL QUESTIONS FROM curated_questions
            if interview.curated_questions and 'questions' in interview.curated_questions:
                questions_list = interview.curated_questions['questions']
                conv_round = 1
                for q_data in questions_list:
                    q_type = q_data.get('question_type', 'technical')
                    custom_text = q_data.get('prompt') or q_data.get('question_text') or q_data.get('text', '')
                    
                    if q_type == 'conversational':
                        session_question = InterviewSessionQuestion(
                            id=uuid.uuid4(),
                            interview_session_id=new_session.id,
                            section_id=section_map["conversational"],
                            question_type="conversational",
                            conversation_round=conv_round,
                            custom_text=custom_text,
                            order=order_idx
                        )
                        uow.session.add(session_question)
                        conv_round += 1
                        order_idx += 1
                    else:
                        question_id = None
                        if 'question_id' in q_data:
                            try:
                                question_id = uuid.UUID(q_data['question_id'])
                            except:
                                question_id = None
                        
                        session_question = InterviewSessionQuestion(
                            id=uuid.uuid4(),
                            interview_session_id=new_session.id,
                            section_id=section_map["technical"],
                            question_type="technical",
                            question_id=question_id,
                            custom_text=custom_text if not question_id else None,
                            order=order_idx
                        )
                        uow.session.add(session_question)
                        order_idx += 1
                    
            # 2. ADD CODING AND CONVERSATIONAL QUESTIONS FROM TEMPLATE
            if interview.template_id:
                from app.db.sql.models.interview_template import InterviewTemplate
                from app.services.template_engine import template_engine, CodingProblemItem, ConversationalRoundItem
                
                template = await uow.session.get(InterviewTemplate, interview.template_id)
                if template:
                    generated_items = await template_engine.generate_interview_questions(template, uow.session)
                    for item in generated_items:
                        if isinstance(item, CodingProblemItem):
                            session_q = InterviewSessionQuestion(
                                interview_session_id=new_session.id,
                                section_id=section_map["coding"],
                                question_type="coding",
                                coding_problem_id=item.coding_problem_id,
                                order=order_idx,
                            )
                            uow.session.add(session_q)
                            order_idx += 1
                        elif isinstance(item, ConversationalRoundItem):
                            session_q = InterviewSessionQuestion(
                                interview_session_id=new_session.id,
                                section_id=section_map["conversational"],
                                question_type="conversational",
                                conversation_round=item.conversation_round,
                                order=order_idx,
                            )
                            uow.session.add(session_q)
                            order_idx += 1

            await uow.flush()

            return {
                "session_id": str(new_session.id),
                "interview_id": str(interview_id),
                "status": InterviewStatus.IN_PROGRESS.value,
            }

    @staticmethod
    async def list_candidate_interviews(session: AsyncSession, candidate_id: uuid.UUID) -> list:
        async with UnitOfWork(session) as uow:
            interviews = await uow.interviews.list_by_candidate(candidate_id)
            
            # Filter out interviews that have expired (72 hours from scheduled_at)
            now_utc = datetime.now(timezone.utc)
            valid_interviews = []
            for i in interviews:
                if i.scheduled_at:
                    expiration_time = i.scheduled_at + timedelta(hours=72)
                    if now_utc > expiration_time:
                        continue  # Skip expired interviews
                valid_interviews.append(i)
            
            return [{
                "id": str(i.id),
                "template_id": str(i.template_id) if i.template_id else None,
                "status": i.status.value,
                "scheduled_at": i.scheduled_at,
                "started_at": i.started_at,
                "completed_at": i.completed_at,
                "overall_score": i.overall_score
            } for i in valid_interviews]
