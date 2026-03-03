import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.sql.session import AsyncSessionLocal
from app.db.sql.models.interview import Interview
from app.db.sql.models.interview_template import InterviewTemplate
from app.db.sql.models.interview_session_question import InterviewSessionQuestion
from app.db.sql.models.user import User
from app.db.sql.enums import UserRole, InterviewStatus

async def verify_db_persistence():
    async with AsyncSessionLocal() as session:
        # 1. Setup: Use existing admin, candidate, template, and question
        admin = (await session.execute(select(User).where(User.role == UserRole.ADMIN).limit(1))).scalar_one_or_none()
        candidate = (await session.execute(select(User).where(User.role == UserRole.CANDIDATE).limit(1))).scalar_one_or_none()
        template = (await session.execute(select(InterviewTemplate).limit(1))).scalar_one_or_none()
        from app.db.sql.models.question import Question
        question = (await session.execute(select(Question).limit(1))).scalar_one_or_none()

        if not (admin and candidate and template and question):
            print("Missing seed data to run test.")
            return

        print(f"Testing direct persistence for interview with custom questions...")
        
        # 2. Create Interview manually
        interview = Interview(
            candidate_id=candidate.id,
            template_id=template.id,
            assigned_by=admin.id,
            status=InterviewStatus.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc),
            curated_questions={"mock": "data"} 
        )
        session.add(interview)
        await session.flush()
        
        # 3. Create InterviewSessionQuestions
        q1 = InterviewSessionQuestion(
            interview_id=interview.id,
            question_id=None,
            custom_text="Custom question text 1",
            order=0
        )
        q2 = InterviewSessionQuestion(
            interview_id=interview.id,
            question_id=question.id, # Real bank ID
            custom_text="Bank question override 2",
            order=1
        )
        session.add_all([q1, q2])
        await session.flush()
        
        # 4. Verify
        result = await session.execute(
            select(InterviewSessionQuestion)
            .where(InterviewSessionQuestion.interview_id == interview.id)
            .order_by(InterviewSessionQuestion.order)
        )
        questions = result.scalars().all()
        print(f"Persisted {len(questions)} questions.")
        assert len(questions) == 2
        assert questions[0].custom_text == "Custom question text 1"
        assert questions[1].custom_text == "Bank question override 2"
        
        print("DB Persistence Verification Successful!")
        await session.rollback()

if __name__ == "__main__":
    asyncio.run(verify_db_persistence())
