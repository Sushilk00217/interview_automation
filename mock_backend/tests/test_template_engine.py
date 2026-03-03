import asyncio
import uuid
from sqlalchemy import select
from app.db.sql.session import AsyncSessionLocal
from app.db.sql.models.interview_template import InterviewTemplate, TemplateQuestion
from app.db.sql.models.question import Question, DifficultyEnum, CategoryEnum
from app.db.sql.models.interview import Interview
from app.db.sql.models.interview_session_question import InterviewSessionQuestion
from app.services.template_engine import template_engine
from app.services.interview_admin_sql_service import InterviewAdminSQLService
from datetime import datetime, timedelta, timezone

async def verify_template_engine():
    async with AsyncSessionLocal() as session:
        # 1. Setup: Ensure some questions exist
        result = await session.execute(select(Question).limit(10))
        questions = result.scalars().all()
        if len(questions) < 5:
            print("Not enough questions in DB to test. Please seed first.")
            return

        # 2. Test Fixed Template
        fixed_template = InterviewTemplate(
            title="Test Fixed Template",
            is_rule_based=False,
            is_active=True
        )
        session.add(fixed_template)
        await session.flush()
        
        tq1 = TemplateQuestion(template_id=fixed_template.id, question_id=questions[0].id, order=0, question_type="static")
        tq2 = TemplateQuestion(template_id=fixed_template.id, question_id=questions[1].id, order=1, question_type="static")
        session.add_all([tq1, tq2])
        await session.flush()
        
        generated_fixed = await template_engine.generate_questions_from_template(fixed_template.id, session)
        print(f"Fixed template generated {len(generated_fixed)} questions.")
        assert len(generated_fixed) == 2
        assert generated_fixed[0].id == questions[0].id

        # 3. Test Rule-based Template
        rule_template = InterviewTemplate(
            title="Test Rule Template",
            is_rule_based=True,
            is_active=True,
            settings={
                "difficulty_distribution": {"EASY": 1, "MEDIUM": 1},
                "category_filters": [q.category.value for q in questions[:5]]
            }
        )
        session.add(rule_template)
        await session.flush()
        
        generated_rule = await template_engine.generate_questions_from_template(rule_template.id, session)
        print(f"Rule-based template generated {len(generated_rule)} questions.")
        # Depending on seed data, this might be 2 if distribution matches
        
        # 4. Test Integration in Scheduling
        # Find a candidate
        from app.db.sql.models.user import User
        from app.db.sql.enums import UserRole
        result = await session.execute(select(User).where(User.role == UserRole.CANDIDATE).limit(1))
        candidate = result.scalar_one_or_none()
        
        result = await session.execute(select(User).where(User.role == UserRole.ADMIN).limit(1))
        admin = result.scalar_one_or_none()
        
        if candidate and admin:
            print(f"Testing scheduling with template {fixed_template.id} for candidate {candidate.id}")
            interview = await InterviewAdminSQLService.create_interview(
                session=session,
                template_id=fixed_template.id,
                candidate_id=candidate.id,
                assigned_by=admin.id,
                scheduled_at=datetime.now(timezone.utc) + timedelta(days=1)
            )
            
            # Verify InterviewSessionQuestion records
            result = await session.execute(
                select(InterviewSessionQuestion)
                .where(InterviewSessionQuestion.interview_id == interview.id)
                .order_by(InterviewSessionQuestion.order)
            )
            is_questions = result.scalars().all()
            print(f"Created {len(is_questions)} SessionQuestion records for interview.")
            assert len(is_questions) == 2
            assert is_questions[0].question_id == questions[0].id
        else:
            print("Skipping scheduling test: candidate or admin not found.")

        await session.rollback() # Don't commit test data
        print("Verification successful (rolled back).")

if __name__ == "__main__":
    asyncio.run(verify_template_engine())
