from pydantic import BaseModel, Field
from typing import Optional, List, Any, Literal
from datetime import datetime


# ─── Request Schemas ─────────────────────────────────────────────────────────

class ScheduleInterviewRequest(BaseModel):
    """Request body for POST /admin/interviews/schedule"""
    candidate_id: str = Field(..., description="UUID of the candidate user")
    template_id: str = Field(..., description="UUID of the interview template")
    scheduled_at: datetime = Field(..., description="Future UTC datetime for the interview")


class RescheduleInterviewRequest(BaseModel):
    """Request body for PUT /admin/interviews/{id}/reschedule"""
    scheduled_at: datetime = Field(..., description="New future UTC datetime for the interview")


class CancelInterviewRequest(BaseModel):
    """Request body for PUT /admin/interviews/{id}/cancel"""
    reason: Optional[str] = Field(None, description="Optional cancellation reason for audit")


class InterviewQuestionSnapshot(BaseModel):
    question_id: Optional[str] = None
    question_text: str
    order: int
    time_limit_sec: int

class ApplyTemplateRequest(BaseModel):
    questions: List[InterviewQuestionSnapshot]


# ─── Response Schemas ─────────────────────────────────────────────────────────

class CuratedQuestionItem(BaseModel):
    """
    A single question in the curated payload.

    Common fields are required for all types.
    Type-specific config blocks are Optional — only the relevant one
    will be populated depending on question_type:
      - "static"         → evaluation_mode + source
      - "conversational" → conversation_config
      - "coding"         → coding_config
    """
    question_id: str
    question_type: Literal["static", "conversational", "coding"]
    order: int
    prompt: str
    difficulty: Literal["easy", "medium", "hard"]
    time_limit_sec: int

    # static-only fields
    evaluation_mode: Optional[str] = None   # e.g. "text"
    source: Optional[str] = None            # e.g. "question_bank"

    # conversational-only fields
    conversation_config: Optional[dict] = None
    # Expected shape:
    # { "follow_up_depth": int, "ai_model": str, "evaluation_mode": str }

    # coding-only fields
    coding_config: Optional[dict] = None
    # Expected shape:
    # { "language": str, "starter_code": str,
    #   "test_cases": [{"input": str, "expected_output": str}],
    #   "execution_timeout_sec": int }

    class Config:
        extra = "allow"   # forward-compatible: extra keys from AI agent won't break deserialization


class CuratedQuestionsPayload(BaseModel):
    template_id: str
    generated_from: dict
    generated_at: datetime
    generation_method: str
    questions: List[CuratedQuestionItem]


class ScheduleInterviewResponse(BaseModel):
    """Response body for POST /admin/interviews/schedule"""
    id: str
    candidate_id: str
    template_id: str
    assigned_by: str
    status: str
    scheduled_at: datetime
    curated_questions: CuratedQuestionsPayload
    created_at: datetime

    class Config:
        from_attributes = True


class RescheduleInterviewResponse(BaseModel):
    """Response body for PUT /admin/interviews/{id}/reschedule"""
    id: str
    status: str
    scheduled_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CancelInterviewResponse(BaseModel):
    """Response body for PUT /admin/interviews/{id}/cancel"""
    id: str
    status: str
    cancelled_at: datetime
    reason: Optional[str] = None

    class Config:
        from_attributes = True
