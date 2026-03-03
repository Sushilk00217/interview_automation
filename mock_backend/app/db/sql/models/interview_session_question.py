import uuid
import datetime
from sqlalchemy import Text, Integer, ForeignKey, CheckConstraint, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql.base import Base

class InterviewSessionQuestion(Base):
    __tablename__ = "interview_session_questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    custom_text: Mapped[str] = mapped_column(Text, nullable=True)
    
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    interview: Mapped["Interview"] = relationship("Interview", back_populates="session_questions")
    question: Mapped["Question"] = relationship("Question")

    __table_args__ = (
        CheckConstraint(
            "(question_id IS NOT NULL) OR (custom_text IS NOT NULL)",
            name="check_question_or_custom_text"
        ),
    )
