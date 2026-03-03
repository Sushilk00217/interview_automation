import uuid
from pydantic import BaseModel, Field
from typing import List
from app.db.sql.models.question import DifficultyEnum, CategoryEnum

class TemplatePreviewQuestion(BaseModel):
    """Schema for a single question in the template preview."""
    question_id: uuid.UUID
    text: str
    difficulty: DifficultyEnum
    category: CategoryEnum

    class Config:
        from_attributes = True

class TemplatePreviewResponse(BaseModel):
    """Response schema for the template preview endpoint."""
    questions: List[TemplatePreviewQuestion]
