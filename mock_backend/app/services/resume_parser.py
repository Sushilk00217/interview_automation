"""
Resume Parser — extract text from uploaded resume (PDF) and parse using Azure OpenAI LLM.
Used to store parsed content for LLM-based question generation when interview starts.
"""

import io
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from app.services.azure_openai_service import azure_openai_service

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "resumes"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF bytes. Returns empty string on failure."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n\n".join(parts).strip() if parts else ""
    except Exception as e:
        logger.warning("PDF text extraction failed: %s", e)
        return ""


def parse_resume_with_llm(resume_text: str) -> Dict[str, Any]:
    """
    Parse resume text using Azure OpenAI LLM to extract structured information.
    
    Returns:
        Dictionary with keys: skills, years_of_experience, education, projects, etc.
    """
    if not azure_openai_service.client:
        logger.warning("Azure OpenAI not configured, using fallback parsing")
        return _fallback_parse_resume(resume_text)
    
    try:
        system_prompt = """You are an expert resume parser. Extract structured information from the resume text.
Focus on extracting ALL technical skills, programming languages, frameworks, tools, and technologies mentioned.

Return ONLY valid JSON with this exact structure:
{
    "summary": "Brief professional summary (2-3 sentences)",
    "skills": ["skill1", "skill2", ...],  // IMPORTANT: Extract ALL technical skills, languages, frameworks, tools
    "experience_years": <number>,
    "education": [
        {
            "degree": "Degree Name",
            "institution": "University/School",
            "field": "Major/Field of Study",
            "year": "Graduation Year"
        }
    ],
    "projects": [
        {
            "name": "Project Name",
            "description": "Project description",
            "technologies": ["tech1", "tech2"],  // Extract all technologies used
            "duration": "Duration if mentioned"
        }
    ],
    "experience": [
        {
            "company": "Company Name",
            "role": "Job Title",
            "duration": "Duration",
            "responsibilities": ["responsibility1", "responsibility2"],
            "technologies": ["tech1", "tech2"]  // Technologies used in this role
        }
    ],
    "certifications": ["cert1", "cert2"],
    "languages": ["language1", "language2"]
}

IMPORTANT: In the "skills" array, include:
- Programming languages (Python, Java, JavaScript, etc.)
- Frameworks (React, Django, Flask, etc.)
- Databases (PostgreSQL, MySQL, MongoDB, etc.)
- Tools (Docker, Kubernetes, AWS, etc.)
- Technologies (Machine Learning, AI, etc.)
- Any technical skills mentioned anywhere in the resume"""

        user_prompt = f"""Parse the following resume text and extract all relevant information:

{resume_text[:8000]}  # Limit to avoid token limits

Return ONLY the JSON object, no additional text or markdown."""

        response = azure_openai_service.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        parsed_json = json.loads(response.choices[0].message.content)
        
        # Extract additional skills from projects and experience
        all_skills = set(parsed_json.get('skills', []))
        
        # Add technologies from projects
        for project in parsed_json.get('projects', []):
            project_techs = project.get('technologies', [])
            if project_techs:
                all_skills.update(project_techs)
        
        # Add technologies from experience
        for exp in parsed_json.get('experience', []):
            exp_techs = exp.get('technologies', [])
            if exp_techs:
                all_skills.update(exp_techs)
        
        # Update skills list with all found skills
        parsed_json['skills'] = list(all_skills)
        
        logger.info(f"Successfully parsed resume with LLM. Found {len(parsed_json['skills'])} skills")
        logger.debug(f"[ResumeParser] Extracted skills: {parsed_json['skills']}")
        return parsed_json
        
    except Exception as e:
        logger.error(f"Error parsing resume with LLM: {e}")
        return _fallback_parse_resume(resume_text)


def _fallback_parse_resume(resume_text: str) -> Dict[str, Any]:
    """Fallback parsing when LLM is not available."""
    import re
    skills = []
    years_exp = None
    
    # Simple skill extraction
    common_skills = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker', 'kubernetes']
    text_lower = resume_text.lower()
    skills = [s for s in common_skills if s in text_lower]
    
    # Extract years of experience
    match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', text_lower)
    if match:
        years_exp = int(match.group(1))
    
    return {
        "skills": list(set(skills)),
        "experience_years": years_exp,
        "education": {"degrees": [], "institutions": [], "fields_of_study": []},
        "projects": [],
        "experience": [],
        "certifications": [],
        "languages": []
    }


def save_resume_and_extract_text(
    candidate_id: str,
    resume_id: str,
    content: bytes,
    content_type: str,
) -> Tuple[str, Optional[Path], Optional[Dict[str, Any]]]:
    """
    Save resume file to disk, extract text if PDF, and parse with LLM.
    Returns (extracted_text, file_path, parsed_data). file_path is None if save failed.
    """
    ext = "pdf"
    if "pdf" in (content_type or ""):
        ext = "pdf"
    elif "word" in (content_type or "") or "doc" in (content_type or ""):
        ext = "doc"
    else:
        ext = "pdf"
    filename = f"{candidate_id}_{resume_id}.{ext}"
    path = UPLOAD_DIR / filename
    try:
        path.write_bytes(content)
    except Exception as e:
        logger.warning("Failed to save resume file %s: %s", path, e)
        return "", None, None
    
    text = ""
    parsed_data = None
    if ext == "pdf":
        text = extract_text_from_pdf(content)
        if text:
            # Parse with LLM
            parsed_data = parse_resume_with_llm(text)
    
    return text, path, parsed_data
