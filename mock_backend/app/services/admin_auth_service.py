import uuid
import os
import logging
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.sql.unit_of_work import UnitOfWork
from app.db.sql.models.user import User, AdminProfile, CandidateProfile
from app.db.sql.models.interview_response import InterviewResponse
from app.db.sql.enums import UserRole
from app.core.security import get_password_hash
from app.schemas.auth import AdminRegistrationRequest
from app.services.azure_verification_service import azure_verification_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class AdminAuthSQLService:
    @staticmethod
    async def register_admin(session: AsyncSession, request: AdminRegistrationRequest) -> User:
        async with UnitOfWork(session) as uow:
            # 1. Unique validations
            existing_user_by_email = await uow.users.get_by_email(request.email)
            if existing_user_by_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
                
            existing_user_by_username = await uow.users.get_by_username(request.username)
            if existing_user_by_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this username already exists"
                )

            # 2. Hash password securely
            hashed_password = get_password_hash(request.password)

            # 3. Create Admin Instance
            new_user = User(
                username=request.username,
                email=request.email,
                role=UserRole.ADMIN,
                hashed_password=hashed_password,
            )

            profile = AdminProfile(
                first_name=request.profile.first_name,
                last_name=request.profile.last_name,
                department=request.profile.department,
                designation=request.profile.designation
            )
            
            new_user.admin_profile = profile
            
            # 4. Attach to Unit of Work Layer
            uow.users.create_user(new_user)
            
            # Flush to hydrate DB ids for response
            await uow.flush()
            
            # 5. Commit naturally when escaping the context block
            return new_user

    @staticmethod
    async def delete_candidate(session: AsyncSession, candidate_id: uuid.UUID) -> bool:
        """
        Deletes a candidate with all dependencies including files and Azure profiles.
        """
        async with UnitOfWork(session) as uow:
            # 1. Fetch candidate with profile and all related data
            user = await uow.users.get_by_id(candidate_id)
            if not user:
                raise HTTPException(status_code=404, detail="Candidate not found")
                
            if user.role != UserRole.CANDIDATE:
                raise HTTPException(status_code=400, detail="User is not a candidate")

            profile = user.candidate_profile
            
            # 2. Gather file paths to delete
            files_to_delete = []
            if profile:
                if profile.resume_path:
                    files_to_delete.append(os.path.normpath(os.path.join(settings.BASE_DIR, profile.resume_path)))
                if profile.face_sample_url:
                    files_to_delete.append(profile.face_sample_url)
                if profile.video_sample_url:
                    files_to_delete.append(profile.video_sample_url)
                if profile.voice_sample_url:
                    files_to_delete.append(profile.voice_sample_url)
                    
            # 3. Gather interview response audio files
            from sqlalchemy import select
            from app.db.sql.models.interview_session import InterviewSession
            responses_stmt = select(InterviewResponse.answer_audio_url).join(InterviewSession).where(
                InterviewSession.candidate_id == candidate_id
            )
            resp_result = await session.execute(responses_stmt)
            for audio_url in resp_result.scalars().all():
                if audio_url and os.path.isabs(audio_url): # Check if it's a file path
                    files_to_delete.append(audio_url)
            
            # 4. Delete Azure profiles (Background or await)
            if profile:
                if profile.face_verification_id:
                    await azure_verification_service.delete_face_person(profile.face_verification_id)
                if profile.voice_profile_id:
                    await azure_verification_service.delete_voice_profile(profile.voice_profile_id)

            # 5. Delete from DB (Cascades should handle it)
            await session.delete(user)
            await uow.flush()
            
            # 6. Physical File Deletion
            for file_path in files_to_delete:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete file {file_path}: {e}")
            
            return True
