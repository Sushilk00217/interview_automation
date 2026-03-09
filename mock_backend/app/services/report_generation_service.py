"""
Report Generation Service
Generates comprehensive interview reports with scores, feedback, and recommendations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.sql.models.interview_session import InterviewSession
from app.db.sql.models.interview_response import InterviewResponse
from app.db.sql.models.interview_session_question import InterviewSessionQuestion
from app.db.sql.models.interview import Interview
from app.db.sql.models.user import CandidateProfile

logger = logging.getLogger(__name__)


class ReportGenerationService:
    """Service for generating interview reports."""
    
    @staticmethod
    async def generate_interview_report(
        session: AsyncSession,
        interview_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive interview report.
        
        Args:
            session: Database session
            interview_id: Interview UUID string
            session_id: Optional session UUID string (if not provided, uses latest session)
            
        Returns:
            Dictionary containing full report with scores, feedback, recommendations
        """
        import uuid
        
        interview_uuid = uuid.UUID(interview_id)
        
        # Get interview
        interview_stmt = select(Interview).where(Interview.id == interview_uuid)
        interview_result = await session.execute(interview_stmt)
        interview = interview_result.scalar_one_or_none()
        
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")
        
        # Get session (use provided or latest)
        if session_id:
            session_uuid = uuid.UUID(session_id)
            session_stmt = select(InterviewSession).where(
                InterviewSession.id == session_uuid,
                InterviewSession.interview_id == interview_uuid
            )
        else:
            session_stmt = select(InterviewSession).where(
                InterviewSession.interview_id == interview_uuid
            ).order_by(InterviewSession.started_at.desc())
        
        session_result = await session.execute(session_stmt)
        interview_session = session_result.scalar_one_or_none()
        
        if not interview_session:
            raise ValueError(f"Interview session not found for interview {interview_id}")
        
        # Get all responses with questions
        responses_stmt = (
            select(InterviewResponse, InterviewSessionQuestion)
            .join(
                InterviewSessionQuestion,
                InterviewResponse.question_id == InterviewSessionQuestion.id
            )
            .where(InterviewResponse.session_id == interview_session.id)
            .order_by(InterviewResponse.submitted_at)
        )
        responses_result = await session.execute(responses_stmt)
        responses_data = responses_result.all()
        
        # Get candidate profile
        candidate_stmt = select(CandidateProfile).where(
            CandidateProfile.user_id == interview.candidate_id
        )
        candidate_result = await session.execute(candidate_stmt)
        candidate_profile = candidate_result.scalar_one_or_none()
        
        # Calculate statistics
        all_scores = [r[0].ai_score for r in responses_data if r[0].ai_score is not None]
        average_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        max_score = max(all_scores) if all_scores else 0.0
        min_score = min(all_scores) if all_scores else 0.0
        
        # Extract strengths and weaknesses from evaluations
        strengths = []
        weaknesses = []
        for resp, q in responses_data:
            if resp.evaluation_json:
                eval_data = resp.evaluation_json
                if isinstance(eval_data, dict):
                    strengths.extend(eval_data.get('strengths', []))
                    weaknesses.extend(eval_data.get('weaknesses', []))
        
        # Deduplicate and limit
        unique_strengths = list(set(strengths))[:5]
        unique_weaknesses = list(set(weaknesses))[:5]
        
        # Generate recommendation
        recommendation = ReportGenerationService._generate_recommendation(
            average_score, unique_strengths, unique_weaknesses
        )
        
        # Build question-by-question breakdown
        question_breakdown = []
        for resp, q in responses_data:
            question_text = q.custom_text or (q.question.text if q.question else "Question")
            question_breakdown.append({
                "question_id": str(q.id),
                "question_text": question_text,
                "question_type": getattr(q, "question_type", "technical"),
                "answer_text": resp.answer_text or "Audio answer",
                "score": resp.ai_score,
                "feedback": resp.ai_feedback,
                "strengths": resp.evaluation_json.get('strengths', []) if resp.evaluation_json else [],
                "weaknesses": resp.evaluation_json.get('weaknesses', []) if resp.evaluation_json else [],
                "submitted_at": resp.submitted_at.isoformat() if resp.submitted_at else None
            })
        
        # Build report
        report = {
            "interview_id": interview_id,
            "session_id": str(interview_session.id),
            "candidate_id": str(interview.candidate_id),
            "candidate_name": candidate_profile.first_name + " " + candidate_profile.last_name if candidate_profile else "Unknown",
            "interview_date": interview_session.started_at.isoformat() if interview_session.started_at else None,
            "completed_at": interview_session.completed_at.isoformat() if interview_session.completed_at else None,
            "overall_score": round(average_score, 2),
            "max_score": round(max_score, 2),
            "min_score": round(min_score, 2),
            "total_questions": len(question_breakdown),
            "answered_questions": len(question_breakdown),
            "recommendation": recommendation["decision"],
            "recommendation_reason": recommendation["reason"],
            "strengths": unique_strengths,
            "weaknesses": unique_weaknesses,
            "question_breakdown": question_breakdown,
            "proctoring_summary": {
                "face_verification_alerts": interview_session.face_verification_alerts or 0,
                "voice_verification_alerts": interview_session.voice_verification_alerts or 0,
                "termination_reason": interview_session.termination_reason
            },
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        logger.info(f"Generated report for interview {interview_id}")
        return report
    
    @staticmethod
    def _generate_recommendation(
        average_score: float,
        strengths: List[str],
        weaknesses: List[str]
    ) -> Dict[str, str]:
        """Generate hiring recommendation based on score and feedback."""
        if average_score >= 8.0:
            decision = "STRONG_HIRE"
            reason = f"Excellent performance with average score of {average_score:.1f}/10. Candidate demonstrates strong technical knowledge and problem-solving skills."
        elif average_score >= 6.5:
            decision = "HIRE"
            reason = f"Good performance with average score of {average_score:.1f}/10. Candidate shows solid understanding and potential."
        elif average_score >= 5.0:
            decision = "CONSIDER"
            reason = f"Average performance with score of {average_score:.1f}/10. Candidate shows promise but may need additional evaluation."
        else:
            decision = "NO_HIRE"
            reason = f"Below average performance with score of {average_score:.1f}/10. Candidate may not meet the required technical standards."
        
        if strengths:
            reason += f" Key strengths: {', '.join(strengths[:3])}."
        if weaknesses:
            reason += f" Areas for improvement: {', '.join(weaknesses[:3])}."
        
        return {
            "decision": decision,
            "reason": reason
        }


report_generation_service = ReportGenerationService()
