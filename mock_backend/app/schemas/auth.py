from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str

class CandidateResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    login_disabled: bool
    created_at: datetime
    job_description: Optional[str] = None
    parse_status: Optional[str] = None
    parsed_at: Optional[datetime] = None
    resume_json: Optional[dict] = None
    jd_json: Optional[dict] = None
    role_name: Optional[str] = None
    match_score: Optional[float] = None
    password: Optional[str] = None

    class Config:
        from_attributes = True

class PaginatedCandidateResponse(BaseModel):
    data: List[CandidateResponse]
    total: int
    limit: int
    offset: int

class AdminProfilePayload(BaseModel):
    first_name: str
    last_name: str
    department: str
    designation: str

class AdminRegistrationRequest(BaseModel):
    username: str
    email: str
    password: str
    profile: AdminProfilePayload

class AdminResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    created_at: datetime
    role: str

    class Config:
        from_attributes = True
