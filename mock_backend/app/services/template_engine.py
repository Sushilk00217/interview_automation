import uuid
import random
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.sql.models.interview_template import InterviewTemplate, TemplateQuestion
from app.db.sql.models.question import Question, DifficultyEnum, CategoryEnum

logger = logging.getLogger(__name__)

class TemplateEngineService:
    @staticmethod
    async def generate_questions_from_template(
        template_id: uuid.UUID,
        session: AsyncSession
    ) -> List[Question]:
        """
        Generates a list of questions based on the template configuration.
        If is_rule_based is True, selects random questions based on distribution.
        Otherwise, returns the fixed questions defined in the template.
        """
        # Load template with its fixed questions
        result = await session.execute(
            select(InterviewTemplate)
            .where(InterviewTemplate.id == template_id)
            .options(selectinload(InterviewTemplate.questions).selectinload(TemplateQuestion.question))
        )
        template = result.scalar_one_or_none()
        
        if not template:
            return []

        if template.is_rule_based:
            return await TemplateEngineService._generate_rule_based_questions(template, session)
        else:
            # Sort by order and return questions
            sorted_template_questions = sorted(template.questions, key=lambda x: x.order)
            return [tq.question for tq in sorted_template_questions if tq.question]

    @staticmethod
    async def _generate_rule_based_questions(
        template: InterviewTemplate,
        session: AsyncSession
    ) -> List[Question]:
        """
        Logic for rule-based generation:
        Expects template.settings to have:
        {
            "difficulty_distribution": {"EASY": 2, "MEDIUM": 3, "HARD": 1},
            "category_filters": ["PYTHON", "SQL"]
        }
        """
        settings = template.settings or {}
        distribution = settings.get("difficulty_distribution", {})
        categories = settings.get("category_filters", [])
        
        generated_questions = []
        
        # Sort distribution keys to ensure difficulty blocks are processed in a deterministic order (e.g., EASY->MEDIUM->HARD)
        # We'll use a specific order: EASY, then MEDIUM, then HARD.
        difficulty_order = {DifficultyEnum.EASY: 0, DifficultyEnum.MEDIUM: 1, DifficultyEnum.HARD: 2}
        sorted_difficulties = sorted(
            distribution.keys(), 
            key=lambda d: difficulty_order.get(DifficultyEnum(d) if d in DifficultyEnum.__members__ else d, 99)
        )

        for difficulty_str in sorted_difficulties:
            count = distribution[difficulty_str]
            try:
                difficulty = DifficultyEnum(difficulty_str)
            except ValueError:
                continue
                
            query = select(Question).where(
                Question.difficulty == difficulty,
                Question.is_active == True
            )
            
            # Exclude already selected questions to be 100% sure of no duplicates
            if generated_questions:
                excluded_ids = [q.id for q in generated_questions]
                query = query.where(Question.id.not_in(excluded_ids))
            
            # Category filters: If empty, it naturally means "all categories"
            if categories:
                cat_enums = []
                for cat_str in categories:
                    try:
                        cat_enums.append(CategoryEnum(cat_str))
                    except ValueError:
                        continue
                if cat_enums:
                    query = query.where(Question.category.in_(cat_enums))
            
            # Use random order for rule-based, deterministic LIMIT within this difficulty block
            query = query.order_by(func.random()).limit(count)
            
            result = await session.execute(query)
            batch = result.scalars().all()
            
            if len(batch) < count:
                logger.warning(
                    f"Could not satisfy distribution for {difficulty_str}. "
                    f"Requested {count}, found {len(batch)}."
                )

            generated_questions.extend(batch)
            
        # We DO NOT shuffle here to maintain "Deterministic order within each difficulty block"
        # The questions will appear in the order of sorted_difficulties.
        return generated_questions

template_engine = TemplateEngineService()
