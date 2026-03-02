import logging
from sqlalchemy import select, literal
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.sql.models.interview_template import InterviewTemplate, TemplateQuestion

logger = logging.getLogger(__name__)

async def seed_templates(session: AsyncSession):
    """Seed default interview templates if none exist."""
    logger.info("Checking for existing interview templates...")
    
    stmt = (
        select(literal(1))
        .select_from(InterviewTemplate)
        .where(InterviewTemplate.is_active == True)
        .limit(1)
    )
    result = await session.execute(stmt)
    already_exists = result.scalar() is not None

    if already_exists:
        logger.info("[template_seed] Active template already exists. Skipping.")
        return

    logger.info("[template_seed] No active templates found. Creating default template...")
    template = InterviewTemplate(
        title="Default Data Science Interview",
        description="Baseline template with coding + conversational questions",
        is_active=True,
        settings={"total_duration_sec": 3600},
    )
    session.add(template)
    await session.flush() # Get template ID

    questions = [
        TemplateQuestion(
            template_id=template.id,
            question_text="Explain a machine learning project you worked on.",
            question_type="CONVERSATIONAL",
            time_limit_sec=120,
            order=1,
        ),
        TemplateQuestion(
            template_id=template.id,
            question_text="Write a SQL query to find the second highest salary.",
            question_type="CODING",
            time_limit_sec=300,
            order=2,
        ),
        TemplateQuestion(
            template_id=template.id,
            question_text="How do you handle model overfitting?",
            question_type="CONVERSATIONAL",
            time_limit_sec=120,
            order=3,
        ),
    ]
    session.add_all(questions)
    logger.info("[OK] Default template created successfully.")
