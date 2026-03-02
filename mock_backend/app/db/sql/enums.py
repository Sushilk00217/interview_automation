import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CANDIDATE = "candidate"

class InterviewStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PENDING_REVIEW = "pending_review"
