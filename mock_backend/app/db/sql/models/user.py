import uuid
import datetime
from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.sql.base import Base
from app.db.sql.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    login_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    admin_profile: Mapped["AdminProfile"] = relationship("AdminProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

class AdminProfile(Base):
    __tablename__ = "admin_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    department: Mapped[str] = mapped_column(String, nullable=True)
    designation: Mapped[str] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="admin_profile")

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    resume_id: Mapped[str] = mapped_column(String, nullable=True)
    experience_years: Mapped[int] = mapped_column(nullable=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    job_description: Mapped[str] = mapped_column(String, nullable=True)  # Store JD text
    resume_text: Mapped[str] = mapped_column(String, nullable=True)  # Store parsed resume text for question generation
    
    # Parsing Architecture Fields
    resume_filename: Mapped[str] = mapped_column(String, nullable=True)
    resume_path: Mapped[str] = mapped_column(String, nullable=True)
    resume_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    jd_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    match_score: Mapped[float] = mapped_column(nullable=True)
    parse_status: Mapped[str] = mapped_column(String, default="pending")
    parsed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Verification fields
    face_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    voice_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    face_sample_url: Mapped[str] = mapped_column(String, nullable=True)  # URL to stored face sample
    video_sample_url: Mapped[str] = mapped_column(String, nullable=True)  # URL to stored video sample
    voice_sample_url: Mapped[str] = mapped_column(String, nullable=True)  # URL to stored voice sample
    face_verification_id: Mapped[str] = mapped_column(String, nullable=True)  # Azure Face API person ID
    voice_profile_id: Mapped[str] = mapped_column(String, nullable=True)  # Azure Speech profile ID

    user: Mapped["User"] = relationship("User", back_populates="candidate_profile")
