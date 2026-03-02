"""
Resume and Job Description Parser Service
------------------------------------------
Parses resume PDFs and job descriptions to extract relevant information
for question generation.
"""

import os
import logging
from typing import Dict, Any, Optional
import PyPDF2
import io

logger = logging.getLogger(__name__)


class ResumeJDParser:
    """Service to parse resume PDFs and job descriptions."""
    
    @staticmethod
    def parse_resume_pdf(resume_path: str) -> Dict[str, Any]:
        """
        Parse a resume PDF file and extract key information.
        
        Args:
            resume_path: Path to the resume PDF file
            
        Returns:
            Dictionary containing parsed resume data:
            - text: Full text content
            - projects: List of projects mentioned
            - skills: List of skills
            - experience: Experience details
            - education: Education details
        """
        try:
            with open(resume_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = []
                
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
                
                full_text = "\n".join(text_content)
                
                # Extract structured information
                parsed_data = ResumeJDParser._extract_resume_info(full_text)
                parsed_data['text'] = full_text
                
                return parsed_data
        except Exception as e:
            logger.error(f"Error parsing resume PDF: {e}")
            return {
                'text': '',
                'projects': [],
                'skills': [],
                'experience': {},
                'education': {}
            }
    
    @staticmethod
    def parse_resume_from_bytes(resume_bytes: bytes) -> Dict[str, Any]:
        """
        Parse a resume PDF from bytes.
        
        Args:
            resume_bytes: PDF file content as bytes
            
        Returns:
            Dictionary containing parsed resume data
        """
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(resume_bytes))
            text_content = []
            
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
            full_text = "\n".join(text_content)
            
            # Extract structured information
            parsed_data = ResumeJDParser._extract_resume_info(full_text)
            parsed_data['text'] = full_text
            
            return parsed_data
        except Exception as e:
            logger.error(f"Error parsing resume from bytes: {e}")
            return {
                'text': '',
                'projects': [],
                'skills': [],
                'experience': {},
                'education': {}
            }
    
    @staticmethod
    def parse_job_description(jd_text: str) -> Dict[str, Any]:
        """
        Parse a job description text.
        
        Args:
            jd_text: Job description text
            
        Returns:
            Dictionary containing parsed JD data:
            - text: Full JD text
            - required_skills: List of required skills
            - responsibilities: List of responsibilities
            - requirements: List of requirements
        """
        return {
            'text': jd_text,
            'required_skills': ResumeJDParser._extract_skills(jd_text),
            'responsibilities': ResumeJDParser._extract_sections(jd_text, ['responsibilities', 'duties', 'what you will']),
            'requirements': ResumeJDParser._extract_sections(jd_text, ['requirements', 'qualifications', 'must have'])
        }
    
    @staticmethod
    def _extract_resume_info(text: str) -> Dict[str, Any]:
        """Extract structured information from resume text."""
        text_lower = text.lower()
        
        # Extract projects (look for project sections)
        projects = ResumeJDParser._extract_projects(text)
        
        # Extract skills
        skills = ResumeJDParser._extract_skills(text)
        
        # Extract experience
        experience = ResumeJDParser._extract_experience(text)
        
        # Extract education
        education = ResumeJDParser._extract_education(text)
        
        return {
            'projects': projects,
            'skills': skills,
            'experience': experience,
            'education': education
        }
    
    @staticmethod
    def _extract_projects(text: str) -> list:
        """Extract project information from resume."""
        projects = []
        lines = text.split('\n')
        
        # Look for project-related keywords
        project_keywords = ['project', 'developed', 'built', 'created', 'implemented']
        current_project = None
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if line contains project keywords
            if any(keyword in line_lower for keyword in project_keywords):
                if current_project:
                    projects.append(current_project)
                
                # Try to extract project name and description
                current_project = {
                    'name': line.strip()[:100],  # First 100 chars as name
                    'description': line.strip(),
                    'technologies': []
                }
                
                # Look ahead for technologies
                for j in range(i+1, min(i+5, len(lines))):
                    next_line = lines[j].lower()
                    tech_keywords = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker', 'kubernetes', 'ml', 'ai', 'tensorflow', 'pytorch']
                    found_techs = [tech for tech in tech_keywords if tech in next_line]
                    if found_techs:
                        current_project['technologies'].extend(found_techs)
            elif current_project and line.strip():
                # Continue building current project description
                current_project['description'] += ' ' + line.strip()
        
        if current_project:
            projects.append(current_project)
        
        return projects[:5]  # Return top 5 projects
    
    @staticmethod
    def _extract_skills(text: str) -> list:
        """Extract skills from text."""
        common_skills = [
            'python', 'java', 'javascript', 'typescript', 'react', 'node.js', 'sql', 
            'postgresql', 'mongodb', 'aws', 'azure', 'docker', 'kubernetes', 
            'machine learning', 'deep learning', 'tensorflow', 'pytorch', 
            'scikit-learn', 'pandas', 'numpy', 'git', 'ci/cd', 'rest api', 
            'graphql', 'microservices', 'agile', 'scrum'
        ]
        
        text_lower = text.lower()
        found_skills = [skill for skill in common_skills if skill in text_lower]
        
        return list(set(found_skills))  # Remove duplicates
    
    @staticmethod
    def _extract_experience(text: str) -> Dict[str, Any]:
        """Extract experience information."""
        # Simple extraction - can be enhanced
        return {
            'years': ResumeJDParser._extract_years_of_experience(text),
            'companies': ResumeJDParser._extract_companies(text)
        }
    
    @staticmethod
    def _extract_years_of_experience(text: str) -> Optional[int]:
        """Extract years of experience."""
        import re
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience:\s*(\d+)\+?\s*years?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    @staticmethod
    def _extract_companies(text: str) -> list:
        """Extract company names (simplified)."""
        # This is a simplified version - can be enhanced with NER
        companies = []
        lines = text.split('\n')
        
        for line in lines:
            # Look for lines that might contain company names
            if any(keyword in line.lower() for keyword in ['inc', 'ltd', 'corp', 'technologies', 'solutions']):
                companies.append(line.strip())
        
        return companies[:5]  # Return top 5
    
    @staticmethod
    def _extract_education(text: str) -> Dict[str, Any]:
        """Extract education information."""
        education_keywords = ['bachelor', 'master', 'phd', 'degree', 'university', 'college']
        text_lower = text.lower()
        
        education = {
            'degrees': [],
            'institutions': []
        }
        
        for keyword in education_keywords:
            if keyword in text_lower:
                # Find the line containing the keyword
                for line in text.split('\n'):
                    if keyword in line.lower():
                        education['degrees'].append(line.strip())
                        break
        
        return education
    
    @staticmethod
    def _extract_sections(text: str, keywords: list) -> list:
        """Extract sections based on keywords."""
        sections = []
        lines = text.split('\n')
        in_section = False
        current_section = []
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in keywords):
                in_section = True
                current_section = [line.strip()]
            elif in_section:
                if line.strip():
                    current_section.append(line.strip())
                else:
                    if current_section:
                        sections.append(' '.join(current_section))
                        current_section = []
                    in_section = False
        
        if current_section:
            sections.append(' '.join(current_section))
        
        return sections


resume_jd_parser = ResumeJDParser()
