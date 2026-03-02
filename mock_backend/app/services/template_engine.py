import uuid
import random
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.sql.models import InterviewTemplate, Question, TemplateQuestion, DifficultyEnum, CategoryEnum

async def generate_questions_from_template(
    session: AsyncSession,
    template_id: uuid.UUID
) -> list[Question]:
    """
    Generates a list of questions based on the template.
    If the template is rule-based, it samples questions from the bank.
    Otherwise, it returns the pre-defined questions in the template.
    """
    # 1. Fetch template
    stmt = select(InterviewTemplate).where(InterviewTemplate.id == template_id)
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()
    
    if not template:
        raise ValueError(f"Template with id {template_id} not found")

    if template.is_rule_based:
        # 2. Logic for rule-based template
        category_filters = template.category_filters
        difficulty_distribution = template.difficulty_distribution or {}
        
        all_selected_questions = []
        selected_ids = set()
        
        for difficulty_str, count in difficulty_distribution.items():
            if count <= 0:
                continue
                
            try:
                difficulty_enum = DifficultyEnum(difficulty_str)
            except ValueError:
                # Skip or raise error if invalid difficulty in distribution
                continue
                
            # Query pool
            query = select(Question).where(
                Question.is_active == True,
                Question.difficulty == difficulty_enum
            )
            
            if category_filters:
                # Convert string filters to CategoryEnum if needed, 
                # but models usually store Enums. Let's assume input filters are strings.
                valid_categories = []
                for cat in category_filters:
                    try:
                        valid_categories.append(CategoryEnum(cat))
                    except ValueError:
                        continue
                if valid_categories:
                    query = query.where(Question.category.in_(valid_categories))
            
            if selected_ids:
                query = query.where(Question.id.notin_(list(selected_ids)))
            
            res = await session.execute(query)
            pool = res.scalars().all()
            
            if len(pool) < count:
                raise ValueError(
                    f"Insufficient questions in pool for difficulty {difficulty_str}. "
                    f"Requested {count}, found {len(pool)}."
                )
            
            sampled = random.sample(pool, count)
            all_selected_questions.extend(sampled)
            selected_ids.update(q.id for q in sampled)
            
        # Shuffle result to mix difficulties if desired, or keep grouped
        random.shuffle(all_selected_questions)
        return all_selected_questions

    else:
        # 3. Logic for fixed template
        stmt = (
            select(Question)
            .join(TemplateQuestion, TemplateQuestion.question_id == Question.id)
            .where(TemplateQuestion.template_id == template_id)
            .order_by(TemplateQuestion.order)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())
