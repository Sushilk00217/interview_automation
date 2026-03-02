import logging
from typing import Optional

logger = logging.getLogger(__name__)

def calculate_match_score(resume_json: Optional[dict], jd_json: Optional[dict]) -> float:
    """
    Deterministic Resume-JD Match Scoring system.
    Returns a score between 0.0 and 100.0 rounded to 2 decimals.
    """
    if not resume_json or not jd_json:
        return 0.0

    total_score = 0.0

    # 1. Skills Matching (60% weight)
    # ---------------------------------------------------------
    resume_skills = set(str(s).lower().strip() for s in resume_json.get("skills", []))
    
    # Extract jd_json["required_skills"] or fallback to jd_json["skills"]
    jd_required_skills = jd_json.get("required_skills")
    if jd_required_skills is None:
        jd_required_skills = jd_json.get("skills", [])
    
    jd_skills = set(str(s).lower().strip() for s in jd_required_skills)
    
    skills_score = 0.0
    if jd_skills:
        intersection = resume_skills.intersection(jd_skills)
        ratio = len(intersection) / max(len(jd_skills), 1)
        skills_score = ratio * 60.0
    
    total_score += skills_score

    # 2. Experience Matching (25% weight)
    # ---------------------------------------------------------
    resume_exp = resume_json.get("experience_years")
    if resume_exp is None:
        # Try to parse from string if it's not a number
        try:
             resume_exp = float(resume_json.get("years_experience", 0))
        except (ValueError, TypeError):
             resume_exp = 0.0
    
    jd_min_exp = jd_json.get("min_years_experience")
    if jd_min_exp is None:
        # Try finding in root or fallback
        jd_min_exp = jd_json.get("experience_required", 0)

    try:
        resume_exp = float(resume_exp)
        jd_min_exp = float(jd_min_exp)
    except (ValueError, TypeError):
        resume_exp = 0.0
        jd_min_exp = 0.0

    exp_score = 0.0
    if jd_min_exp <= 0:
        # If no experience required, award full points if they have any, or 12.5 if 0
        exp_score = 25.0 if resume_exp >= 0 else 0.0
    else:
        if resume_exp >= jd_min_exp:
            exp_score = 25.0
        else:
            # Proportional score for having some experience but less than required
            exp_score = (resume_exp / jd_min_exp) * 25.0
    
    total_score += exp_score

    # 3. Education Matching (15% weight)
    # ---------------------------------------------------------
    resume_edu = resume_json.get("education", [])
    jd_edu_required = jd_json.get("education_required") or jd_json.get("education")

    edu_score = 7.5 # Neutral score default
    
    if resume_edu and jd_edu_required:
        # Basic keyword match
        res_edu_str = str(resume_edu).lower()
        req_edu_str = str(jd_edu_required).lower()
        
        # Checking for common degrees if specified
        common_degrees = ["bachelor", "master", "phd", "b.tech", "m.tech", "mba", "computer science"]
        matched = False
        for degree in common_degrees:
            if degree in req_edu_str and degree in res_edu_str:
                matched = True
                break
        
        if matched:
            edu_score = 15.0
        elif any(word in res_edu_str for word in req_edu_str.split()):
            # Fallback fuzzy word match
            edu_score = 12.0
        else:
            edu_score = 5.0
            
    total_score += edu_score

    return round(min(total_score, 100.0), 2)
