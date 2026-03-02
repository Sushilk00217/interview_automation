import uuid
import datetime
from sqlalchemy import String, DateTime, Float, Enum, ForeignKey, JSON, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql.base import Base
from app.db.sql.enums import InterviewStatus

class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_templates.id", ondelete="SET NULL"), nullable=True)
    assigned_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    status: Mapped[InterviewStatus] = mapped_column(Enum(InterviewStatus), default=InterviewStatus.SCHEDULED, index=True)
    
    scheduled_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str] = mapped_column(String, nullable=True)
    
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)
    feedback: Mapped[str] = mapped_column(String, nullable=True)
    
    curated_questions: Mapped[list] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate: Mapped["User"] = relationship("User", foreign_keys=[candidate_id])
    assigner: Mapped["User"] = relationship("User", foreign_keys=[assigned_by])
    template: Mapped["InterviewTemplate"] = relationship("InterviewTemplate", back_populates="interviews")
    sessions: Mapped[list["InterviewSession"]] = relationship("InterviewSession", back_populates="interview", cascade="all, delete-orphan")
    session_questions: Mapped[list["InterviewSessionQuestion"]] = relationship("InterviewSessionQuestion", back_populates="interview", cascade="all, delete-orphan")

class InterviewSessionQuestion(Base):
    __tablename__ = "interview_session_questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    
    question_text: Mapped[str] = mapped_column(String, nullable=False)  # snapshot copy
    order: Mapped[int] = mapped_column(Integer, default=0)
    time_limit_sec: Mapped[int] = mapped_column(Integer, default=120)
    
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    interview: Mapped["Interview"] = relationship("Interview", back_populates="session_questions")
    question: Mapped["Question"] = relationship("Question")
