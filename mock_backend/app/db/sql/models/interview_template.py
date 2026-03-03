import uuid
import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql.base import Base

class InterviewTemplate(Base):
    __tablename__ = "interview_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False, default="Untitled Template")
    role_name: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default_for_role: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    settings: Mapped[dict] = mapped_column(JSON, nullable=True)
    is_rule_based: Mapped[bool] = mapped_column(Boolean, default=False)

    questions: Mapped[list["TemplateQuestion"]] = relationship("TemplateQuestion", back_populates="template", cascade="all, delete-orphan")
    interviews: Mapped[list["Interview"]] = relationship("Interview", back_populates="template")

class TemplateQuestion(Base):
    __tablename__ = "template_questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_templates.id", ondelete="CASCADE"), nullable=False)
    
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    
    question_type: Mapped[str] = mapped_column(String, nullable=False)
    time_limit_sec: Mapped[int] = mapped_column(Integer, default=120)
    order: Mapped[int] = mapped_column(Integer, default=0)
    
    template: Mapped["InterviewTemplate"] = relationship("InterviewTemplate", back_populates="questions")
    question: Mapped["Question"] = relationship("Question", back_populates="template_questions")
