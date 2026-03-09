import uuid
import datetime
import enum
from sqlalchemy import Text, JSON, Boolean, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql.base import Base

class DifficultyEnum(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"

class CategoryEnum(str, enum.Enum):
    PYTHON = "PYTHON"
    SQL = "SQL"
    MACHINE_LEARNING = "MACHINE_LEARNING"
    DATA_STRUCTURES = "DATA_STRUCTURES"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"
    STATISTICS = "STATISTICS"

class QuestionType(str, enum.Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CODING = "coding"

class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[CategoryEnum] = mapped_column(SQLEnum(CategoryEnum), nullable=False)
    difficulty: Mapped[DifficultyEnum] = mapped_column(SQLEnum(DifficultyEnum), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=True) # Usually list[str] for tags
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    question_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(
            QuestionType,
            name="questiontype",
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False,
        server_default="technical"
    )
