"""
Question Generator Service
--------------------------
Generates interview questions using Azure OpenAI GPT-4o based on parsed resume and JD.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from app.services.resume_jd_parser import resume_jd_parser
from app.services.azure_openai_service import azure_openai_service

logger = logging.getLogger(__name__)


class QuestionGeneratorService:
    """Service to generate interview questions from resume and JD."""
    
    # Directory where resumes are stored
    RESUME_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "resumes")
    
    @staticmethod
    def generate_curated_questions(
        template_id: str,
        candidate_id: str,
        resume_id: Optional[str] = None,
        resume_text: Optional[str] = None,
        job_description: Optional[str] = None,
    ) -> dict:
        """
        Generate curated questions based on resume and JD using Azure OpenAI.
        
        Args:
            template_id: UUID string of the interview template
            candidate_id: UUID string of the candidate
            resume_id: Resume identifier (used as fallback to find resume file)
            resume_text: Parsed resume text from database (preferred)
            job_description: Job description text
            
        Returns:
            dict conforming to CuratedQuestionsPayload schema
        """
        try:
            # Use stored resume_text if available, otherwise parse from file
            if resume_text:
                # Use stored resume text directly
                resume_data = {
                    'text': resume_text,
                    'projects': [],
                    'skills': [],
                    'experience': {},
                    'education': {}
                }
                # Try to parse structured data if possible (optional enhancement)
                try:
                    parsed = resume_jd_parser.parse_resume_pdf_from_text(resume_text) if hasattr(resume_jd_parser, 'parse_resume_pdf_from_text') else resume_data
                    resume_data = parsed if parsed else resume_data
                except:
                    pass  # Use basic text if parsing fails
            else:
                # Fallback to parsing from file
                resume_data = QuestionGeneratorService._parse_resume(resume_id)
            
            # Parse job description
            jd_data = resume_jd_parser.parse_job_description(job_description or "")
            
            # Generate questions using Azure OpenAI
            questions = azure_openai_service.generate_conversational_questions(
                resume_data=resume_data,
                jd_data=jd_data,
                num_questions=5
            )
            
            return {
                "template_id": template_id,
                "generated_from": {
                    "resume_id": resume_id or candidate_id,
                    "jd_id": "jd_from_registration",
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "generation_method": "azure_openai_gpt4o",
                "questions": questions
            }
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            # Fallback to mock questions
            return QuestionGeneratorService._generate_fallback_questions(template_id, candidate_id, resume_id)
    
    @staticmethod
    def _parse_resume(resume_id: Optional[str]) -> Dict[str, Any]:
        """Parse resume file if available."""
        if not resume_id:
            return {
                'text': '',
                'projects': [],
                'skills': [],
                'experience': {},
                'education': {}
            }
        
        try:
            # Try to find resume file
            resume_path = os.path.join(QuestionGeneratorService.RESUME_UPLOAD_DIR, f"{resume_id}.pdf")
            
            if os.path.exists(resume_path):
                return resume_jd_parser.parse_resume_pdf(resume_path)
            else:
                logger.warning(f"Resume file not found: {resume_path}")
                return {
                    'text': '',
                    'projects': [],
                    'skills': [],
                    'experience': {},
                    'education': {}
                }
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            return {
                'text': '',
                'projects': [],
                'skills': [],
                'experience': {},
                'education': {}
            }
    
    @staticmethod
    def _generate_fallback_questions(
        template_id: str,
        candidate_id: str,
        resume_id: Optional[str]
    ) -> dict:
        """Generate fallback mock questions if generation fails."""
        return {
            "template_id": template_id,
            "generated_from": {
                "resume_id": resume_id or candidate_id,
                "jd_id": "fallback",
            },
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generation_method": "fallback_mock",
            "questions": [
                {
                    "question_id": "conv_q_001",
                    "question_type": "conversational",
                    "order": 1,
                    "prompt": "Tell me about a challenging project you worked on. What technologies did you use?",
                    "difficulty": "medium",
                    "time_limit_sec": 300,
                    "conversation_config": {
                        "follow_up_depth": 2,
                        "ai_model": "gpt-4o",
                        "evaluation_mode": "contextual"
                    }
                },
                {
                    "question_id": "conv_q_002",
                    "question_type": "conversational",
                    "order": 2,
                    "prompt": "Walk me through your approach to solving a complex technical problem.",
                    "difficulty": "medium",
                    "time_limit_sec": 300,
                    "conversation_config": {
                        "follow_up_depth": 2,
                        "ai_model": "gpt-4o",
                        "evaluation_mode": "contextual"
                    }
                },
                {
                    "question_id": "conv_q_003",
                    "question_type": "conversational",
                    "order": 3,
                    "prompt": "Deep dive into the architecture of your most complex project. What were the main challenges?",
                    "difficulty": "hard",
                    "time_limit_sec": 600,
                    "conversation_config": {
                        "follow_up_depth": 3,
                        "ai_model": "gpt-4o",
                        "evaluation_mode": "contextual"
                    }
                },
                {
                    "question_id": "conv_q_004",
                    "question_type": "conversational",
                    "order": 4,
                    "prompt": "Explain how you would optimize a system for scalability and performance.",
                    "difficulty": "hard",
                    "time_limit_sec": 600,
                    "conversation_config": {
                        "follow_up_depth": 3,
                        "ai_model": "gpt-4o",
                        "evaluation_mode": "contextual"
                    }
                },
                {
                    "question_id": "conv_q_005",
                    "question_type": "conversational",
                    "order": 5,
                    "prompt": "If you had to redesign a system you built, what would you do differently and why?",
                    "difficulty": "hard",
                    "time_limit_sec": 600,
                    "conversation_config": {
                        "follow_up_depth": 3,
                        "ai_model": "gpt-4o",
                        "evaluation_mode": "contextual"
                    }
                }
            ]
        }


question_generator_service = QuestionGeneratorService()
