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

async def parse_candidate_resume(candidate_id: uuid.UUID):
    """
    Background task to parse candidate's resume and job description.
    """
    async with AsyncSessionLocal() as session:
        async with UnitOfWork(session) as uow:
            try:
                # Fetch candidate profile
                user = await uow.users.get_by_id(candidate_id)
                if not user or not user.candidate_profile:
                    logger.error(f"Candidate profile not found for id {candidate_id}")
                    return
                
                profile = user.candidate_profile
                
                # Parse resume
                resume_json = None
                if profile.resume_text:
                    try:
                        resume_json = resume_jd_parser._extract_resume_info(profile.resume_text)
                        resume_json['text'] = profile.resume_text
                    except Exception as e:
                        logger.error(f"Error parsing structured resume for candidate {candidate_id}: {e}")
                
                # Parse job description
                jd_json = None
                if profile.job_description:
                    try:
                        jd_json = resume_jd_parser.parse_job_description(profile.job_description)
                    except Exception as e:
                        logger.error(f"Error parsing job description for candidate {candidate_id}: {e}")
                
                profile.resume_json = resume_json
                profile.jd_json = jd_json
                
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
