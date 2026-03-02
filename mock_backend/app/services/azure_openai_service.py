"""
Azure OpenAI Service
--------------------
Service to interact with Azure OpenAI GPT-4o for question generation.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from openai import AzureOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """Service to interact with Azure OpenAI."""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure OpenAI client."""
        try:
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            
            if not azure_endpoint or not api_key:
                logger.warning("Azure OpenAI credentials not configured. Question generation will use mock data.")
                return None
            
            self.client = AzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version=api_version
            )
            logger.info("Azure OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            self.client = None
    
    def generate_conversational_questions(
        self,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        num_questions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate conversational questions based on resume and JD.
        
        Args:
            resume_data: Parsed resume data
            jd_data: Parsed job description data
            num_questions: Number of questions to generate (default: 5)
            
        Returns:
            List of question dictionaries with difficulty progression
        """
        if not self.client:
            logger.warning("Azure OpenAI not configured, returning mock questions")
            return self._generate_mock_questions(resume_data, jd_data, num_questions)
        
        try:
            # Extract projects from resume
            projects = resume_data.get('projects', [])
            if not projects:
                # Fallback to skills if no projects found
                projects = [{'name': 'General Experience', 'description': resume_data.get('text', '')[:500]}]
            
            # Build prompt for question generation
            prompt = self._build_question_generation_prompt(
                projects=projects,
                resume_skills=resume_data.get('skills', []),
                jd_requirements=jd_data.get('requirements', []),
                jd_skills=jd_data.get('required_skills', [])
            )
            
            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o",  # or your deployment name
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical interviewer. Generate conversational interview questions based on the candidate's resume and job requirements. Focus on projects and technologies mentioned."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse response
            questions = self._parse_question_response(response.choices[0].message.content)
            
            # Ensure we have the right number and difficulty progression
            return self._format_questions_with_difficulty(questions, num_questions, projects)
            
        except Exception as e:
            logger.error(f"Error generating questions with Azure OpenAI: {e}")
            return self._generate_mock_questions(resume_data, jd_data, num_questions)
    
    def _build_question_generation_prompt(
        self,
        projects: List[Dict[str, Any]],
        resume_skills: List[str],
        jd_requirements: List[str],
        jd_skills: List[str]
    ) -> str:
        """Build the prompt for question generation."""
        projects_text = "\n".join([
            f"Project: {p.get('name', 'Unknown')}\nDescription: {p.get('description', '')[:300]}\nTechnologies: {', '.join(p.get('technologies', []))}"
            for p in projects[:3]  # Focus on top 3 projects
        ])
        
        prompt = f"""Generate 5 conversational interview questions based on the following information:

CANDIDATE PROJECTS:
{projects_text}

CANDIDATE SKILLS:
{', '.join(resume_skills[:20])}

JOB REQUIREMENTS:
{chr(10).join(jd_requirements[:5]) if jd_requirements else 'Not specified'}

REQUIRED SKILLS:
{', '.join(jd_skills[:20])}

INSTRUCTIONS:
1. First 2 questions should be MEDIUM difficulty - ask about project overview, technologies used, and basic implementation details
2. Next 3 questions should be HARD difficulty - test deep understanding of:
   - Architecture decisions and trade-offs
   - Performance optimization
   - Problem-solving approaches
   - Edge cases and challenges faced
   - Advanced concepts related to technologies used

Format your response as JSON array with this structure:
[
  {{
    "question": "Question text here",
    "difficulty": "medium" or "hard",
    "focus_area": "Brief description of what this tests",
    "follow_up_depth": 3
  }}
]

Return ONLY the JSON array, no additional text."""
        
        return prompt
    
    def _parse_question_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse the response from Azure OpenAI."""
        import json
        import re
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group())
                return questions
            else:
                # Fallback: try to parse entire response
                questions = json.loads(response_text)
                return questions
        except Exception as e:
            logger.error(f"Error parsing question response: {e}")
            return []
    
    def _format_questions_with_difficulty(
        self,
        questions: List[Dict[str, Any]],
        num_questions: int,
        projects: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format questions with proper difficulty progression."""
        formatted = []
        
        # Ensure we have medium questions first, then hard
        medium_questions = [q for q in questions if q.get('difficulty', '').lower() == 'medium'][:2]
        hard_questions = [q for q in questions if q.get('difficulty', '').lower() == 'hard'][:3]
        
        # If we don't have enough, generate some
        while len(medium_questions) < 2:
            medium_questions.append({
                'question': f"Tell me about one of your projects involving {projects[0].get('name', 'your work') if projects else 'your experience'}. What technologies did you use and why?",
                'difficulty': 'medium',
                'focus_area': 'Project overview and technology selection',
                'follow_up_depth': 2
            })
        
        while len(hard_questions) < 3:
            hard_questions.append({
                'question': f"Deep dive into the architecture of {projects[0].get('name', 'your project') if projects else 'your most complex project'}. What were the main challenges and how did you solve them?",
                'difficulty': 'hard',
                'focus_area': 'Deep technical understanding and problem-solving',
                'follow_up_depth': 3
            })
        
        # Combine and format
        all_questions = medium_questions[:2] + hard_questions[:3]
        
        for i, q in enumerate(all_questions[:num_questions], 1):
            formatted.append({
                'question_id': f"conv_q_{i:03d}",
                'question_type': 'conversational',
                'order': i,
                'prompt': q.get('question', ''),
                'difficulty': q.get('difficulty', 'medium'),
                'time_limit_sec': 300 if q.get('difficulty') == 'medium' else 600,
                'conversation_config': {
                    'follow_up_depth': q.get('follow_up_depth', 3),
                    'ai_model': 'gpt-4o',
                    'evaluation_mode': 'contextual',
                    'focus_area': q.get('focus_area', '')
                }
            })
        
        return formatted
    
    def _generate_mock_questions(
        self,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        num_questions: int
    ) -> List[Dict[str, Any]]:
        """Generate mock questions when Azure OpenAI is not available."""
        projects = resume_data.get('projects', [])
        project_name = projects[0].get('name', 'your project') if projects else 'your experience'
        
        questions = [
            {
                'question_id': 'conv_q_001',
                'question_type': 'conversational',
                'order': 1,
                'prompt': f"Tell me about {project_name}. What was your role and what technologies did you use?",
                'difficulty': 'medium',
                'time_limit_sec': 300,
                'conversation_config': {
                    'follow_up_depth': 2,
                    'ai_model': 'gpt-4o',
                    'evaluation_mode': 'contextual'
                }
            },
            {
                'question_id': 'conv_q_002',
                'question_type': 'conversational',
                'order': 2,
                'prompt': f"Walk me through the implementation approach for {project_name}. What were the key design decisions?",
                'difficulty': 'medium',
                'time_limit_sec': 300,
                'conversation_config': {
                    'follow_up_depth': 2,
                    'ai_model': 'gpt-4o',
                    'evaluation_mode': 'contextual'
                }
            },
            {
                'question_id': 'conv_q_003',
                'question_type': 'conversational',
                'order': 3,
                'prompt': f"Deep dive into the architecture of {project_name}. What were the main scalability challenges and how did you address them?",
                'difficulty': 'hard',
                'time_limit_sec': 600,
                'conversation_config': {
                    'follow_up_depth': 3,
                    'ai_model': 'gpt-4o',
                    'evaluation_mode': 'contextual'
                }
            },
            {
                'question_id': 'conv_q_004',
                'question_type': 'conversational',
                'order': 4,
                'prompt': f"Explain the most complex technical problem you faced in {project_name}. How did you debug and solve it?",
                'difficulty': 'hard',
                'time_limit_sec': 600,
                'conversation_config': {
                    'follow_up_depth': 3,
                    'ai_model': 'gpt-4o',
                    'evaluation_mode': 'contextual'
                }
            },
            {
                'question_id': 'conv_q_005',
                'question_type': 'conversational',
                'order': 5,
                'prompt': f"If you had to redesign {project_name} today, what would you do differently and why? What advanced patterns or technologies would you consider?",
                'difficulty': 'hard',
                'time_limit_sec': 600,
                'conversation_config': {
                    'follow_up_depth': 3,
                    'ai_model': 'gpt-4o',
                    'evaluation_mode': 'contextual'
                }
            }
        ]
        
        return questions[:num_questions]


azure_openai_service = AzureOpenAIService()
