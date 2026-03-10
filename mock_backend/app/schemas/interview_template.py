import uuid
from pydantic import BaseModel, Field
from typing import List, Optional
from app.db.sql.models.question import DifficultyEnum, CategoryEnum

class TemplatePreviewQuestion(BaseModel):
    """Schema for a single question in the template preview."""
    question_id: Optional[uuid.UUID] = None
    text: str
    difficulty: str  # Can be string or enum
    category: str  # Can be string or enum

    class Config:
        from_attributes = True

class TechnicalSectionPreview(BaseModel):
    questions: List[TemplatePreviewQuestion]

class CodingSectionProblemPreview(BaseModel):
    problem_id: uuid.UUID
    title: str
    difficulty: str
    starter_code: Optional[dict] = None

class CodingSectionPreview(BaseModel):
    problems: List[CodingSectionProblemPreview]

class ConversationalSectionPreview(BaseModel):
    rounds: int
    description: str

class TemplatePreviewResponse(BaseModel):
    """Response schema for the template preview endpoint."""
    technical_section: TechnicalSectionPreview
    coding_section: CodingSectionPreview
    conversational_section: ConversationalSectionPreview
