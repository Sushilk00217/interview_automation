import os
import logging
import uuid
from datetime import timedelta, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.auth import TokenResponse, LoginRequest, CandidateResponse, AdminRegistrationRequest, AdminResponse, PaginatedCandidateResponse
from app.db.sql.session import get_db_session
from app.db.sql.unit_of_work import UnitOfWork
from app.db.sql.models.user import User, CandidateProfile, AdminProfile
from app.db.sql.enums import UserRole
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.config import settings
from app.services.email_service import email_service
from app.services.admin_auth_service import AdminAuthSQLService
from app.services.resume_tasks import parse_candidate_resume

logger = logging.getLogger(__name__)
CANDIDATE_MATERIALS_COLLECTION = "candidate_materials"
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def validate_uuid(id_str: str) -> uuid.UUID:
    try:
        return uuid.UUID(id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid UUID: {id_str}",
        )

async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_db_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
            
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    async with UnitOfWork(session) as uow:
        user = await uow.users.get_by_id(user_id)
        if user is None:
            raise credentials_exception
        return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    return current_user

@router.post("/register/candidate", response_model=TokenResponse)
async def register_candidate(user_data: dict, session: AsyncSession = Depends(get_db_session)):
    """Warning: mock route. Uses direct dictionary rather than Pydantic struct to bypass typing logic conflicts temporarily during migration."""
    raise HTTPException(status_code=501, detail="Direct unauthenticated registration is intentionally disabled. Admins must provision candidates natively.")

@router.post("/register/admin", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
async def register_admin(request: AdminRegistrationRequest, session: AsyncSession = Depends(get_db_session)):
    """
    Register a new administrator into the platform securely via SQL repositories.
    """
    user = await AdminAuthSQLService.register_admin(session=session, request=request)
    
    return AdminResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        role=user.role.value,
        created_at=user.created_at
    )

@router.post("/login/admin", response_model=TokenResponse)
async def login_admin(request: LoginRequest, session: AsyncSession = Depends(get_db_session)):
    try:
        async with UnitOfWork(session) as uow:
            user = await uow.users.get_by_username(request.username)
            
            if not user or not verify_password(request.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect admin credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if user.role != UserRole.ADMIN:
                 raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not an admin",
                )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=str(user.id), expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username,
            "role": user.role.value
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login_admin: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/login/candidate", response_model=TokenResponse)
async def login_candidate(request: LoginRequest, session: AsyncSession = Depends(get_db_session)):
    try:
        async with UnitOfWork(session) as uow:
            user = await uow.users.get_by_username(request.username)
            
            if not user or not verify_password(request.password, user.hashed_password):
                 raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect candidate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if user.role != UserRole.CANDIDATE:
                 raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not a candidate",
                )
                
            if user.login_disabled:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Login has been disabled for this account. Please contact the administrator."
                )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=str(user.id), expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username,
            "role": user.role.value
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login_candidate: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
    }

@router.post("/logout")
async def logout():
    return {"message": "Successfully logged out"}

# --- Admin Features ---

@router.post("/admin/register-candidate", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def admin_register_candidate(
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    job_description: str = Form(""),
    resume: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    async with UnitOfWork(session) as uow:
        username = candidate_email.split('@')[0]
        
        existing_user = await uow.users.get_by_username(username)
        if existing_user:
             raise HTTPException(status_code=400, detail="Candidate with this email/username already exists")
    
        password = secrets.token_urlsafe(12)
        hashed_password = get_password_hash(password)
        
        resume_id = secrets.token_hex(8)
        
        # Save resume file and extract text
        import os
        import shutil
        from app.services.resume_parser import extract_text_from_pdf
        
        from app.services.resume_parser import extract_text_from_pdf
        
        upload_rel_dir = os.path.join("uploads", "resumes")
        upload_dir = os.path.join(settings.BASE_DIR, upload_rel_dir)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Read resume content
        resume_bytes = await resume.read()
        if len(resume_bytes) == 0:
            raise HTTPException(status_code=400, detail="Resume file is empty")
        
        # Extract text from resume (parse before saving to get text)
        resume_text = ""
        try:
            if resume.content_type and "pdf" in resume.content_type:
                resume_text = extract_text_from_pdf(resume_bytes)
        except Exception as e:
            logger.warning(f"Failed to extract text from resume: {e}")
            resume_text = ""
        
        # Save resume file
        resume_path = os.path.join(upload_dir, f"{resume_id}.pdf")
        try:
            with open(resume_path, "wb") as buffer:
                buffer.write(resume_bytes)
        except Exception as e:
            logger.error(f"Failed to save resume file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save resume file")
        
        names = candidate_name.split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""
        
        new_user = User(
            username=username,
            email=candidate_email,
            role=UserRole.CANDIDATE,
            hashed_password=hashed_password,
        )
        
        profile = CandidateProfile(
            first_name=first_name,
            last_name=last_name,
            resume_id=resume_id,
            skills=[],
            job_description=job_description,  # Store JD in profile
            resume_text=resume_text or "",  # Store parsed resume text
            resume_filename=resume.filename,
            resume_path=os.path.join(upload_rel_dir, f"{resume_id}.pdf"),
            parse_status="pending"
        )
        new_user.candidate_profile = profile
        
        uow.users.create_user(new_user)
        # Flush to get the ID for response
        await uow.flush()
        
        if background_tasks:
            background_tasks.add_task(parse_candidate_resume, new_user.id)
        
        # Print credentials to terminal
        print("\n" + "="*70)
        print(" " * 20 + "CANDIDATE REGISTRATION SUCCESSFUL")
        print("="*70)
        print(f" Candidate Name: {candidate_name}")
        print(f" Email: {candidate_email}")
        print(f" Username: {username}")
        print(f" Password: {password}")
        print(f" Candidate ID: {new_user.id}")
        print("="*70)
        print(" " * 15 + "IMPORTANT: Save these credentials!")
        print("="*70 + "\n")
        
        await email_service.send_candidate_password_email(candidate_email, candidate_name, password)
        
        return CandidateResponse(
            id=str(new_user.id),
            username=new_user.username,
            email=new_user.email,
            is_active=new_user.is_active,
            login_disabled=new_user.login_disabled,
            created_at=new_user.created_at,
            job_description=job_description 
        )

@router.get("/admin/candidates", response_model=PaginatedCandidateResponse)
async def get_all_candidates(
    limit: int = 10,
    offset: int = 0,
    search: str = "",
    sort_by: str = "created_at",
    order: str = "desc",
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    try:
        from sqlalchemy.orm import selectinload
        from sqlalchemy import func, or_, nulls_last
        from app.db.sql.models.user import CandidateProfile
        
        async with UnitOfWork(session) as uow:
            # Base query
            query = select(User).where(User.role == UserRole.CANDIDATE)
            
            # Apply search
            if search:
                search_term = f"%{search}%"
                query = query.outerjoin(User.candidate_profile).where(
                    or_(
                        User.username.ilike(search_term),
                        User.email.ilike(search_term),
                        CandidateProfile.first_name.ilike(search_term),
                        CandidateProfile.last_name.ilike(search_term),
                    )
                )

            # Apply sorting
            sort_field = User.created_at
            if sort_by == "match_score":
                query = query.outerjoin(User.candidate_profile)
                sort_field = CandidateProfile.match_score
            elif sort_by == "username":
                sort_field = User.username

            if order == "desc":
                query = query.order_by(nulls_last(sort_field.desc()))
            else:
                query = query.order_by(nulls_last(sort_field.asc()))

            # Eagerly load candidate_profile to avoid lazy loading issues
            stmt = query.options(selectinload(User.candidate_profile)).offset(offset).limit(limit)
            result = await session.execute(stmt)
            users = result.scalars().all()
            
            # Count total
            count_stmt = select(func.count(User.id)).where(User.role == UserRole.CANDIDATE)
            if search:
                count_stmt = count_stmt.outerjoin(User.candidate_profile).where(
                    or_(
                        User.username.ilike(search_term),
                        User.email.ilike(search_term),
                        CandidateProfile.first_name.ilike(search_term),
                        CandidateProfile.last_name.ilike(search_term),
                    )
                )
            
            total_result = await session.execute(count_stmt)
            total = total_result.scalar() or 0
            
            candidates = []
            for u in users:
                job_desc = None
                if u.candidate_profile:
                    job_desc = u.candidate_profile.job_description
                
                c = CandidateResponse(
                    id=str(u.id),
                    username=u.username,
                    email=u.email,
                    is_active=u.is_active,
                    login_disabled=u.login_disabled,
                    created_at=u.created_at,
                    job_description=job_desc or "",
                    parse_status=u.candidate_profile.parse_status if u.candidate_profile else None,
                    parsed_at=u.candidate_profile.parsed_at if u.candidate_profile else None,
                    resume_json=u.candidate_profile.resume_json if u.candidate_profile else None,
                    jd_json=u.candidate_profile.jd_json if u.candidate_profile else None,
                    match_score=u.candidate_profile.match_score if u.candidate_profile else None
                )
                candidates.append(c)
                
            return {
                "data": candidates,
                "total": total,
                "limit": limit,
                "offset": offset
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_all_candidates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch candidates: {str(e)}"
        )

@router.post("/admin/candidates/{candidate_id}/toggle-login")
async def toggle_candidate_login(
    candidate_id: str, 
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    valid_id = validate_uuid(candidate_id)
    
    async with UnitOfWork(session) as uow:
        # Direct fetch since we only need simple toggling
        user = await uow.users.get_by_id(valid_id)
        if not user:
            raise HTTPException(status_code=404, detail="Candidate not found")
            
        if user.role != UserRole.CANDIDATE:
            raise HTTPException(status_code=400, detail="User is not a candidate")
        
        new_status = not user.login_disabled
        user.login_disabled = new_status
        user.updated_at = datetime.now(timezone.utc)
        
        return {
            "message": f"Candidate login has been {'disabled' if new_status else 'enabled'}",
            "candidate_id": str(user.id),
            "email": user.email,
            "login_disabled": new_status
        }

@router.post("/admin/candidates/{user_id}/reparse-resume", status_code=status.HTTP_202_ACCEPTED)
async def reparse_resume(
    user_id: str,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    valid_id = validate_uuid(user_id)
    
    async with UnitOfWork(session) as uow:
        user = await uow.users.get_by_id(valid_id)
        if not user:
            raise HTTPException(status_code=404, detail="Candidate not found")
            
        if not user.candidate_profile:
            raise HTTPException(status_code=400, detail="Candidate profile not found")
            
        user.candidate_profile.parse_status = "pending"
        user.candidate_profile.updated_at = datetime.now(timezone.utc)
        
        await session.commit()
        
        background_tasks.add_task(parse_candidate_resume, user.id)
        
        return {"message": "Reparsing background task initiated", "user_id": str(user.id)}

@router.get("/admin/candidates/{user_id}/resume-file")
async def get_candidate_resume_file(
    user_id: str,
    current_admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session)
):
    valid_id = validate_uuid(user_id)
    
    async with UnitOfWork(session) as uow:
        user = await uow.users.get_by_id(valid_id)
        if not user or not user.candidate_profile:
            raise HTTPException(status_code=404, detail="Candidate or profile not found")
            
        profile = user.candidate_profile
        if not profile.resume_path:
            raise HTTPException(status_code=404, detail="Resume path not recorded")
            
        # Securely resolve path using BASE_DIR
        # Use normpath to resolve any '..' and join with BASE_DIR
        abs_resume_path = os.path.normpath(os.path.join(settings.BASE_DIR, profile.resume_path))
        
        # Security check: ensure the resolved path starts with the BASE_DIR
        if not abs_resume_path.startswith(os.path.abspath(settings.BASE_DIR)):
            logger.error(f"Potential directory traversal attempt for user {user_id} path {profile.resume_path}")
            raise HTTPException(status_code=400, detail="Invalid file path")
            
        if not os.path.exists(abs_resume_path):
            logger.error(f"Resume file missing at {abs_resume_path} for user {user_id}")
            raise HTTPException(status_code=404, detail="Resume file not found on server")
            
        filename = profile.resume_filename or f"resume_{user_id}.pdf"
        media_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"
        
        headers = {}
        if media_type == "application/pdf":
            headers["Content-Disposition"] = "inline"
        
        return FileResponse(
            path=abs_resume_path,
            filename=filename,
            media_type=media_type,
            headers=headers
        )
