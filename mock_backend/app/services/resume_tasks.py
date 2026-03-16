import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.sql.session import AsyncSessionLocal
from app.db.sql.unit_of_work import UnitOfWork
from app.db.sql.models.user import User, CandidateProfile
from app.services.resume_jd_parser import resume_jd_parser
from app.services.match_score_service import calculate_match_score

logger = logging.getLogger(__name__)

import uuid

async def parse_candidate_resume(candidate_id: uuid.UUID, password: str = None):
    """
    Background task to handle text extraction, candidate notification, 
    and structured parsing of resume/JD.
    """
    import anyio
    import os
    from app.core.config import settings
    from app.services.resume_parser import extract_text_from_pdf, parse_resume_with_llm
    from app.services.email_service import email_service
    
    async with AsyncSessionLocal() as session:
        async with UnitOfWork(session) as uow:
            try:
                # Fetch candidate profile
                user = await uow.users.get_by_id(candidate_id)
                if not user or not user.candidate_profile:
                    logger.error(f"Candidate profile not found for id {candidate_id}")
                    return
                
                profile = user.candidate_profile
                
                # 1. Send Welcome Email (if password provided)
                if password:
                    try:
                        await email_service.send_candidate_password_email(
                            user.email, 
                            profile.first_name, 
                            user.username,
                            password, 
                            resume_path=profile.resume_path
                        )
                    except Exception as e:
                        logger.error(f"Failed to send welcome email to {user.email}: {e}")

                # 2. Extract Text from PDF (if not already extracted)
                if not profile.resume_text and profile.resume_path:
                    try:
                        abs_path = os.path.join(settings.BASE_DIR, profile.resume_path)
                        if os.path.exists(abs_path):
                            with open(abs_path, "rb") as f:
                                resume_bytes = f.read()
                                profile.resume_text = extract_text_from_pdf(resume_bytes)
                    except Exception as e:
                        logger.error(f"Error extracting text from PDF for candidate {candidate_id}: {e}")

                # 3. Structured Resume Parsing (Offload LLM block to thread)
                resume_json = None
                if profile.resume_text:
                    try:
                        resume_json = await anyio.to_thread.run_sync(parse_resume_with_llm, profile.resume_text)
                        if resume_json:
                            resume_json['text'] = profile.resume_text
                    except Exception as e:
                        logger.error(f"Error parsing structured resume for candidate {candidate_id}: {e}", exc_info=True)
                
                # 4. Structured JD Parsing (Offload LLM block to thread)
                jd_json = None
                if profile.job_description:
                    try:
                        jd_json = await anyio.to_thread.run_sync(resume_jd_parser.parse_job_description, profile.job_description)
                    except Exception as e:
                        logger.error(f"Error parsing job description for candidate {candidate_id}: {e}")
                
                profile.resume_json = resume_json
                profile.jd_json = jd_json
                
                # Extract skills and experience from parsed data
                if resume_json:
                    profile.skills = resume_json.get('skills', [])
                    profile.experience_years = resume_json.get('experience_years')
                
                # Deterministic match scoring
                profile.match_score = calculate_match_score(resume_json, jd_json)
                
                profile.parse_status = "success"
                profile.parsed_at = datetime.now(timezone.utc)
                
                await session.commit()
                logger.info(f"Successfully processed structured parsing for candidate {candidate_id}")
                
            except Exception as e:
                logger.error(f"Failed to process structured parsing for candidate {candidate_id}: {e}")
                # Try to safely update status to failed
                try:
                    user = await uow.users.get_by_id(candidate_id)
                    if user and user.candidate_profile:
                        user.candidate_profile.parse_status = "failed"
                        await session.commit()
                except Exception as inner_e:
                    logger.error(f"Failed to set parse_status to 'failed' for {candidate_id}: {inner_e}")
