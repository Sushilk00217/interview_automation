from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.sql.models.interview_template import InterviewTemplate
import logging

logger = logging.getLogger(__name__)

async def seed_templates(session: AsyncSession):
    """Seed default interview templates if they don't exist."""
    logger.info("Seeding Interview Templates...")
    
    templates_data = [
        {
            "title": "Default Rule Template",
            "description": "General purpose interview with technical, coding, and conversational sections.",
            "technical_config": {
                "easy": 2,
                "medium": 2,
                "hard": 1,
                "duration_minutes": 20,
                "question_source": "ai_generated"
            },
            "coding_config": {
                "count": 1,
                "difficulty": ["easy", "medium"],
                "duration_minutes": 30
            },
            "conversational_config": {
                "rounds": 5,
                "duration_minutes": 15
            },
            "settings": {
                "category_filters": []
            }
        },
        {
            "title": "Backend Developer Template",
            "role_name": "Backend Developer",
            "description": "In-depth technical interview for backend roles focusing on system design and algorithms.",
            "technical_config": {
                "easy": 1,
                "medium": 3,
                "hard": 2,
                "duration_minutes": 30,
                "question_source": "ai_generated"
            },
            "coding_config": {
                "count": 2,
                "difficulty": ["medium", "hard"],
                "duration_minutes": 45
            },
            "conversational_config": {
                "rounds": 8,
                "duration_minutes": 20
            },
            "settings": {
                "category_filters": ["PYTHON", "SQL", "SYSTEM_DESIGN", "DATA_STRUCTURES"]
            }
        },
        {
            "title": "Frontend Developer Template",
            "role_name": "Frontend Developer",
            "description": "Focused on UI/UX principles, React, and frontend architecture.",
            "technical_config": {
                "easy": 2,
                "medium": 2,
                "hard": 1,
                "duration_minutes": 25,
                "question_source": "ai_generated"
            },
            "coding_config": {
                "count": 1,
                "difficulty": ["easy", "medium"],
                "duration_minutes": 30
            },
            "conversational_config": {
                "rounds": 6,
                "duration_minutes": 15
            },
            "settings": {
                "category_filters": ["DATA_STRUCTURES", "SYSTEM_DESIGN"] # No specific FRONTEND category in seeds yet
            }
        },
        {
            "title": "Data Scientist Template",
            "role_name": "Data Scientist",
            "description": "Technical interview covering statistics, machine learning, and data processing.",
            "technical_config": {
                "easy": 1,
                "medium": 4,
                "hard": 2,
                "duration_minutes": 35,
                "question_source": "ai_generated"
            },
            "coding_config": {
                "count": 1,
                "difficulty": ["medium"],
                "duration_minutes": 40
            },
            "conversational_config": {
                "rounds": 7,
                "duration_minutes": 20
            },
            "settings": {
                "category_filters": ["MACHINE_LEARNING", "STATISTICS", "SQL", "PYTHON"]
            }
        }
    ]

    for t_data in templates_data:
        # Check if template already exists by title
        stmt = select(InterviewTemplate).where(InterviewTemplate.title == t_data["title"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if not existing:
            logger.info(f"[template_seed] Creating template: {t_data['title']}")
            template = InterviewTemplate(
                title=t_data["title"],
                role_name=t_data.get("role_name"),
                description=t_data["description"],
                is_active=True,
                technical_config=t_data["technical_config"],
                coding_config=t_data["coding_config"],
                conversational_config=t_data["conversational_config"],
                settings=t_data.get("settings", {})
            )
            session.add(template)
        else:
            logger.info(f"[template_seed] Template already exists: {t_data['title']}. Updating configuration.")
            # Update existing template to ensure it has the latest durations and configs
            existing.technical_config = t_data["technical_config"]
            existing.coding_config = t_data["coding_config"]
            existing.conversational_config = t_data["conversational_config"]
            existing.description = t_data["description"]
            existing.role_name = t_data.get("role_name")
            existing.settings = t_data.get("settings", {})

    await session.commit()
    logger.info("[OK] Interview templates seeded/updated.")

