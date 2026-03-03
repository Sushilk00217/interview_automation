import asyncio
import uuid
from sqlalchemy import select
from app.db.sql.session import AsyncSessionLocal
from app.db.sql.models.interview_template import InterviewTemplate
from app.db.sql.models.question import Question, DifficultyEnum, CategoryEnum
from app.services.template_engine import template_engine

async def verify_preview_endpoint():
    async with AsyncSessionLocal() as session:
        # 1. Setup: Ensure some questions exist
        result = await session.execute(select(Question).limit(10))
        questions = result.scalars().all()
        if len(questions) < 5:
            print("Not enough questions in DB to test. Please seed first.")
            return

        # 2. Test Rule-based Template Preview (Happy Path)
        rule_template = InterviewTemplate(
            title="Preview Test Rule Template",
            is_rule_based=True,
            is_active=True,
            settings={
                "difficulty_distribution": {"EASY": 1, "MEDIUM": 1},
                "category_filters": [q.category.value for q in questions[:5]]
            }
        )
        session.add(rule_template)
        await session.flush()
        
        print(f"Testing preview for rule-based template {rule_template.id}")
        generated_rule = await template_engine.generate_questions_from_template(rule_template.id, session)
        print(f"Preview generated {len(generated_rule)} questions.")
        
        # 3. Test Distribution Gap Logging
        print("Testing distribution gap logging (requesting 100 EASY questions)...")
        gap_template = InterviewTemplate(
            title="Gap Test Template",
            is_rule_based=True,
            is_active=True,
            settings={
                "difficulty_distribution": {"EASY": 100}
            }
        )
        session.add(gap_template)
        await session.flush()
        
        # This should trigger the logger.warning in TemplateEngineService
        generated_gap = await template_engine.generate_questions_from_template(gap_template.id, session)
        print(f"Gap preview generated {len(generated_gap)} questions (requested 100).")

        # 4. Cleanup
        await session.rollback()
        print("Verification successful (rolled back).")

if __name__ == "__main__":
    asyncio.run(verify_preview_endpoint())
