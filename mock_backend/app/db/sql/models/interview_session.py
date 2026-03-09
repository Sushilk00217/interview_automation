import uuid
import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql.base import Base

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    current_section_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("interview_session_sections.id", use_alter=True, name="fk_session_current_section", ondelete="SET NULL"), nullable=True)
    
    status: Mapped[str] = mapped_column(String, default="active")
    
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Verification tracking
    face_verification_alerts: Mapped[int] = mapped_column(Integer, default=0)  # Count of face mismatch alerts
    voice_verification_alerts: Mapped[int] = mapped_column(Integer, default=0)  # Count of voice mismatch alerts
    last_face_verification: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_voice_verification: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    termination_reason: Mapped[str] = mapped_column(String, nullable=True)  # Reason if auto-terminated

    interview: Mapped["Interview"] = relationship("Interview", back_populates="sessions")
    candidate: Mapped["User"] = relationship("User", foreign_keys=[candidate_id])
    sections: Mapped[list["InterviewSessionSection"]] = relationship("InterviewSessionSection", back_populates="session", foreign_keys="InterviewSessionSection.interview_session_id", cascade="all, delete-orphan")
    current_section: Mapped["InterviewSessionSection"] = relationship("InterviewSessionSection", foreign_keys=[current_section_id])
    session_questions: Mapped[list["InterviewSessionQuestion"]] = relationship("InterviewSessionQuestion", back_populates="session", cascade="all, delete-orphan")
