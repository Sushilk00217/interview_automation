import uuid
import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql.base import Base


class CodingProblem(Base):
    __tablename__ = "coding_problems"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # FK to questions table — cascade delete so removing the Question removes this too
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String, nullable=False)

    # Per-language starter code, e.g. {"python": "def solution():\n    pass"}
    starter_code: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Maximum allowed time in seconds for the candidate to solve this problem
    time_limit_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=900, server_default="900")

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    question: Mapped["Question"] = relationship("Question")
    test_cases: Mapped[list["TestCase"]] = relationship(
        "TestCase", back_populates="problem", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["CodeSubmission"]] = relationship(
        "CodeSubmission", back_populates="problem", cascade="all, delete-orphan"
    )


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    problem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coding_problems.id", ondelete="CASCADE"),
        nullable=False,
    )

    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)

    # Hidden test cases are not shown to the candidate
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # Display / execution ordering
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    problem: Mapped["CodingProblem"] = relationship("CodingProblem", back_populates="test_cases")


class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    problem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coding_problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    language: Mapped[str] = mapped_column(String, nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)

    # Execution result status, e.g. "accepted", "wrong_answer", "runtime_error", "pending"
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", server_default="pending")

    # Per-test-case execution results stored as JSON
    results: Mapped[dict] = mapped_column(JSON, nullable=True)

    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    submitted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    problem: Mapped["CodingProblem"] = relationship("CodingProblem", back_populates="submissions")
