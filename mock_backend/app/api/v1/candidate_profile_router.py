"""
Candidate Profile Router — face and voice enrollment for verification.
---------------------------------------------------------------------
Used on candidate dashboard to capture live photo and voice for later
face/audio verification during the interview (Azure Face API + Azure Speech Service).
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth_router import get_current_active_user
from app.db.sql.session import get_db_session
from app.db.sql.models.user import User
from app.db.sql.enums import UserRole
from app.db.sql.unit_of_work import UnitOfWork
from app.services.face_service import face_service
from app.services.speech_service import speech_service

router = APIRouter()


async def get_current_candidate(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can access this endpoint",
        )
    return current_user


@router.post(
    "/profile/face",
    summary="Upload live photo for face verification",
    description="Candidate uploads a live camera photo. Stored for face verification during interview (Azure Face API–ready).",
)
async def upload_face(
    current_candidate: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
    photo: UploadFile = File(..., description="Live photo (image/jpeg or image/png)"),
):
    candidate_id = str(current_candidate.id)
    content_type = photo.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (e.g. image/jpeg, image/png)",
        )
    image_bytes = await photo.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image")
    ref_id, path_or_azure_id = face_service.enroll_face(candidate_id, image_bytes, content_type)
    
    async with UnitOfWork(session) as uow:
        candidate = await uow.users.get_by_id(current_candidate.id)
        if not candidate or not candidate.candidate_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found"
            )
        profile = candidate.candidate_profile
        profile.face_verification_id = ref_id
        profile.face_sample_url = path_or_azure_id
        profile.face_verified = True
        candidate.updated_at = datetime.now(timezone.utc)
        await uow.flush()
    
    return {
        "message": "Face enrolled successfully. It will be used for verification during the interview.",
        "face_ref_id": ref_id,
    }


@router.post(
    "/profile/voice",
    summary="Upload live voice recording for audio verification",
    description="Candidate uploads a short voice recording. Stored for voice verification during interview (Azure Speech Service–ready).",
)
async def upload_voice(
    current_candidate: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
    audio: UploadFile = File(..., description="Voice recording (audio/webm, audio/wav, etc.)"),
):
    candidate_id = str(current_candidate.id)
    content_type = audio.content_type or "audio/webm"
    if not content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an audio recording (e.g. audio/webm, audio/wav)",
        )
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio")
    ref_id, path_or_azure_id = speech_service.enroll_voice(candidate_id, audio_bytes, content_type)
    
    async with UnitOfWork(session) as uow:
        candidate = await uow.users.get_by_id(current_candidate.id)
        if not candidate or not candidate.candidate_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found"
            )
        profile = candidate.candidate_profile
        profile.voice_profile_id = ref_id
        profile.voice_sample_url = path_or_azure_id
        profile.voice_verified = True
        candidate.updated_at = datetime.now(timezone.utc)
        await uow.flush()
    
    return {
        "message": "Voice enrolled successfully. It will be used for verification during the interview.",
        "voice_ref_id": ref_id,
    }


@router.get(
    "/profile/verification-status",
    summary="Get face and voice enrollment status",
    description="Returns whether the candidate has enrolled face and voice for interview verification.",
)
async def get_verification_status(
    current_candidate: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_db_session),
):
    async with UnitOfWork(session) as uow:
        candidate = await uow.users.get_by_id(current_candidate.id)
        if not candidate or not candidate.candidate_profile:
            return {
                "face_enrolled": False,
                "voice_enrolled": False,
                "face_updated_at": None,
                "voice_updated_at": None,
            }
        profile = candidate.candidate_profile
        return {
            "face_enrolled": bool(profile.face_verification_id),
            "voice_enrolled": bool(profile.voice_profile_id),
            "face_updated_at": candidate.updated_at.isoformat() if profile.face_verification_id and candidate.updated_at else None,
            "voice_updated_at": candidate.updated_at.isoformat() if profile.voice_profile_id and candidate.updated_at else None,
        }
