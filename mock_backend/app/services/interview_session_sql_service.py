import uuid
import random
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.sql.unit_of_work import UnitOfWork
from app.db.sql.enums import InterviewStatus
from app.db.sql.models.interview_session import InterviewSession
from app.db.sql.models.interview import Interview
from app.db.sql.models.interview_session_question import InterviewSessionQuestion
from app.db.sql.models.interview_response import InterviewResponse
from app.db.sql.models.user import CandidateProfile
from app.db.sql.models.coding_problem import CodingProblem, TestCase
from app.db.sql.models.question import QuestionType
from app.services.answer_evaluation_service import answer_evaluation_service

# ── Mock score generation ──────────────────────────────────────────────────────
_STRENGTH_POOL = [
    "Clear communication and structured thinking",
    "Strong grasp of SQL and data manipulation",
    "Good understanding of ML model evaluation",
    "Solid problem-solving approach",
    "Confident and concise answers",
]
_GAP_POOL = [
    "Could improve depth on neural network architecture",
    "Limited exposure to distributed computing",
    "Overfitting discussion lacked concrete techniques",
    "Could elaborate more on production deployment",
]
_RECOMMENDATIONS = [
    ("PROCEED",  "Strong candidate — recommend moving forward."),
    ("REVIEW",   "Good potential — recommend technical panel review."),
    ("PROCEED",  "Meets bar — proceed to next round."),
]


def _generate_mock_result(interview_id: uuid.UUID) -> Dict[str, Any]:
    """
    Seeded deterministic mock scoring — same interview always gets same result.
    Score range: 70–95.
    """
    rng = random.Random(interview_id.int)
    score = round(rng.uniform(70.0, 95.0), 1)
    recommendation, note = rng.choice(_RECOMMENDATIONS)
    strengths = rng.sample(_STRENGTH_POOL, k=2)
    gaps = rng.sample(_GAP_POOL, k=1)
    fraud_risk = rng.choice(["LOW", "LOW", "LOW", "MEDIUM"])
    return {
        "final_score": score,
        "recommendation": recommendation,
        "fraud_risk": fraud_risk,
        "strengths": strengths,
        "gaps": gaps,
        "notes": note,
    }


class InterviewSessionSQLService:

    @staticmethod
    async def _get_session_and_interview(
        uow: UnitOfWork,
        session_id: uuid.UUID,
        candidate_id: Optional[uuid.UUID] = None,
        with_for_update: bool = False,
    ):
        stmt = select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.status == "active",
        )
        if with_for_update:
            stmt = stmt.with_for_update()

        result = await uow.session.execute(stmt)
        session_obj = result.scalar_one_or_none()

        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or not active",
            )

        if candidate_id and session_obj.candidate_id != candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to you",
            )

        interview = await uow.interviews.get_by_id(
            session_obj.interview_id, with_for_update=with_for_update
        )
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found"
            )

        return session_obj, interview

    @staticmethod
    async def validate_session(
        session: AsyncSession,
        session_id: uuid.UUID,
        candidate_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        async with UnitOfWork(session) as uow:
            session_obj, interview = await InterviewSessionSQLService._get_session_and_interview(
                uow, session_id, candidate_id
            )
            return {
                "session_id": str(session_obj.id),
                "interview_id": str(interview.id),
                "candidate_id": str(session_obj.candidate_id),
                "status": session_obj.status,
            }

    @staticmethod
    async def get_session_state(
        session: AsyncSession,
        session_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> Dict[str, Any]:
        async with UnitOfWork(session) as uow:
            session_obj, interview = await InterviewSessionSQLService._get_session_and_interview(
                uow, session_id, candidate_id
            )

            stmt = (
                select(InterviewSessionQuestion)
                .options(selectinload(InterviewSessionQuestion.question))
                .where(InterviewSessionQuestion.interview_id == interview.id)
                .order_by(InterviewSessionQuestion.order)
            )
            result = await session.execute(stmt)
            questions = result.scalars().all()

            answered_count = session_obj.answered_count

            if answered_count >= len(questions):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="No more questions"
                )

            q = questions[answered_count]
            
            # Get answer_mode and time_limit from curated_questions if available
            answer_mode = "TEXT"
            time_limit_sec = 240  # Default 4 minutes
            
            # Try to get from curated_questions first
            if interview.curated_questions and 'questions' in interview.curated_questions:
                questions_list = interview.curated_questions['questions']
                if answered_count < len(questions_list):
                    q_data = questions_list[answered_count]
                    answer_mode = q_data.get('answer_mode', 'text').upper() or "TEXT"
                    time_limit_sec = q_data.get('time_limit_sec', 240)
            
            # Fallback logic if not in curated_questions
            if answer_mode == "TEXT":
                if q.question:
                    category_name = q.question.category.name if hasattr(q.question.category, 'name') else str(q.question.category)
                    if category_name in ["SQL", "DATA_STRUCTURES"]:
                        answer_mode = "CODE"
                    else:
                        answer_mode = "AUDIO"
                elif q.custom_text:
                    # Fallback to audio for custom text unless we try to guess it's coding
                    answer_mode = "AUDIO"
            
            # Ensure answer_mode is uppercase
            answer_mode = answer_mode.upper() if answer_mode else "TEXT"

            prompt = q.custom_text or (q.question.text if q.question else "Please answer the following question.")

            # ── Coding question branch ────────────────────────────────────────
            if q.question and q.question.question_type == QuestionType.CODING:
                # Look up the associated CodingProblem via question_id
                cp_result = await session.execute(
                    select(CodingProblem).where(CodingProblem.question_id == q.question.id)
                )
                coding_problem = cp_result.scalars().first()

                if not coding_problem:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Coding problem configuration missing for this question.",
                    )

                # Fetch only visible (non-hidden) test cases as examples
                tc_result = await session.execute(
                    select(TestCase)
                    .where(
                        TestCase.problem_id == coding_problem.id,
                        TestCase.is_hidden == False,  # noqa: E712
                    )
                    .order_by(TestCase.order)
                )
                visible_tcs = tc_result.scalars().all()

                examples = [
                    {
                        "input": tc.input,
                        "expected_output": tc.expected_output,
                    }
                    for tc in visible_tcs
                ]

                return {
                    "type": "coding",
                    "question_id": str(q.question.id),
                    "problem_id": str(coding_problem.id),
                    "title": coding_problem.title,
                    "description": coding_problem.description,
                    "starter_code": coding_problem.starter_code or {},
                    "examples": examples,
                    "time_limit_sec": coding_problem.time_limit_sec,
                    # Keep parity fields so the frontend stays consistent
                    "question_number": answered_count + 1,
                    "total_questions": len(questions),
                }
            # ── End coding branch ─────────────────────────────────────────────

            return {
                "question_id": str(q.id),
                "question_text": prompt,
                "answer_mode": answer_mode,
                "time_limit_sec": time_limit_sec,
                "question_number": answered_count + 1,
                "total_questions": len(questions),
            }

    @staticmethod
    async def get_answered_count(
        session: AsyncSession, session_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> int:
        async with UnitOfWork(session) as uow:
            session_obj, _ = await InterviewSessionSQLService._get_session_and_interview(
                uow, session_id, candidate_id
            )
            return session_obj.answered_count

    @staticmethod
    async def submit_answer(
        session: AsyncSession,
        session_id: uuid.UUID,
        candidate_id: uuid.UUID,
        answer_payload: dict,
    ) -> Dict[str, Any]:
        async with UnitOfWork(session) as uow:
            session_obj, interview = await InterviewSessionSQLService._get_session_and_interview(
                uow, session_id, candidate_id, with_for_update=True
            )

            # Get current question
            stmt = (
                select(InterviewSessionQuestion)
                .options(selectinload(InterviewSessionQuestion.question))
                .where(InterviewSessionQuestion.interview_id == interview.id)
                .order_by(InterviewSessionQuestion.order)
            )
            result = await session.execute(stmt)
            questions = result.scalars().all()
            
            answered_count = session_obj.answered_count
            if answered_count >= len(questions):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All questions already answered"
                )
            
            current_question = questions[answered_count]
            
            # Get question data from curated_questions if available
            question_data = None
            curated_questions = interview.curated_questions
            if curated_questions and 'questions' in curated_questions:
                for q in curated_questions['questions']:
                    if q.get('question_id') == str(current_question.id) or q.get('order') == answered_count + 1:
                        question_data = q
                        break
            
            # If not found in curated_questions, build from question object
            if not question_data:
                question_data = {
                    'prompt': current_question.custom_text or (current_question.question.text if current_question.question else ''),
                    'difficulty': current_question.question.difficulty.value.lower() if current_question.question else 'medium',
                    'conversation_config': {}
                }
            
            # Get candidate profile for context
            candidate = await uow.users.get_by_id(candidate_id)
            resume_data = None
            jd_data = None
            if candidate and candidate.candidate_profile:
                profile = candidate.candidate_profile
                resume_data = profile.resume_json or {'text': profile.resume_text or '', 'projects': [], 'skills': profile.skills or []}
                jd_data = profile.jd_json or {'text': profile.job_description or '', 'requirements': [], 'required_skills': []}
            
            # Extract answer
            answer_text = answer_payload.get('answer_payload', '') if answer_payload.get('answer_type') in ['TEXT', 'CODE'] else None
            answer_audio_url = answer_payload.get('answer_payload') if answer_payload.get('answer_type') == 'AUDIO' else None
            answer_mode = answer_payload.get('answer_type', 'TEXT').lower()
            
            # Evaluate answer using LLM
            evaluation = answer_evaluation_service.evaluate_answer(
                question=question_data,
                answer_text=answer_text,
                answer_audio_url=answer_audio_url,
                resume_data=resume_data,
                jd_data=jd_data
            )
            
            # Store response with evaluation
            response = InterviewResponse(
                session_id=session_id,
                question_id=current_question.id,
                answer_text=answer_text,
                answer_audio_url=answer_audio_url,
                answer_mode=answer_mode,
                ai_score=evaluation.get('score'),
                ai_feedback=evaluation.get('feedback'),
                evaluation_json=evaluation
            )
            session.add(response)
            
            new_count = answered_count + 1
            session_obj.answered_count = new_count

            if new_count >= len(questions):
                # ── All questions answered → calculate overall score and complete ──
                now = datetime.now(timezone.utc)
                
                # Calculate average score from all responses
                score_stmt = select(func.avg(InterviewResponse.ai_score)).where(
                    InterviewResponse.session_id == session_id
                )
                avg_score_result = await session.execute(score_stmt)
                avg_score = avg_score_result.scalar() or 0.0
                
                # Convert to 0-100 scale (since scores are 0-10)
                overall_score = (avg_score / 10.0) * 100.0
                
                # Get all evaluations for feedback
                feedback_stmt = select(InterviewResponse).where(
                    InterviewResponse.session_id == session_id
                ).order_by(InterviewResponse.submitted_at)
                feedback_result = await session.execute(feedback_stmt)
                all_responses = feedback_result.scalars().all()
                
                strengths = []
                weaknesses = []
                for resp in all_responses:
                    if resp.evaluation_json:
                        strengths.extend(resp.evaluation_json.get('strengths', []))
                        weaknesses.extend(resp.evaluation_json.get('weaknesses', []))
                
                session_obj.status = "completed"
                session_obj.completed_at = now

                interview.status = InterviewStatus.COMPLETED
                interview.completed_at = now
                interview.overall_score = round(overall_score, 2)
                # Convert sets to lists before slicing (sets are not subscriptable)
                strengths_list = list(set(strengths))[:3] if strengths else []
                weaknesses_list = list(set(weaknesses))[:3] if weaknesses else []
                
                interview.feedback = (
                    f"Overall Score: {overall_score:.1f}/100. "
                    f"Key Strengths: {', '.join(strengths_list) if strengths_list else 'N/A'}. "
                    f"Areas for Improvement: {', '.join(weaknesses_list) if weaknesses_list else 'N/A'}."
                )
                await uow.flush()
                return {"state": "COMPLETED"}
            else:
                await uow.flush()
                return {"state": "IN_PROGRESS"}

    @staticmethod
    async def complete_session(
        session: AsyncSession, session_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Dict[str, Any]:
        async with UnitOfWork(session) as uow:
            session_obj, interview = await InterviewSessionSQLService._get_session_and_interview(
                uow, session_id, candidate_id, with_for_update=True
            )

            now = datetime.now(timezone.utc)
            session_obj.status = "completed"
            session_obj.completed_at = now
            interview.status = InterviewStatus.COMPLETED
            interview.completed_at = now

            return {"state": "COMPLETED"}

    @staticmethod
    async def get_summary(
        session: AsyncSession,
        session_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Return the mock evaluation summary for a completed interview session.
        Score is retrieved from interview.overall_score (written at completion).
        All other fields are regenerated deterministically from the interview ID seed.
        """
        async with UnitOfWork(session) as uow:
            # Allow completed sessions (status != "active") — no active filter here
            stmt = select(InterviewSession).where(InterviewSession.id == session_id)
            result = await uow.session.execute(stmt)
            session_obj = result.scalar_one_or_none()

            if not session_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
                )
            if session_obj.candidate_id != candidate_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Session does not belong to you",
                )

            interview = await uow.interviews.get_by_id(session_obj.interview_id)
            if not interview:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found"
                )

            if interview.overall_score is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Interview not yet completed",
                )

            # Use persisted score; regenerate other fields deterministically
            mock = _generate_mock_result(interview.id)
            return {
                "final_score": interview.overall_score,
                "recommendation": mock["recommendation"],
                "fraud_risk": mock["fraud_risk"],
                "strengths": mock["strengths"],
                "gaps": mock["gaps"],
                "notes": mock["notes"],
                "completed_at": session_obj.completed_at,
            }
