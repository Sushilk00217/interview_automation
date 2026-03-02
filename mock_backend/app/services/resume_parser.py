"""
Resume Parser — extract text from uploaded resume (PDF).
Used to store parsed content for LLM-based question generation when interview starts.
"""

import io
import logging
from pathlib import Path
from typing import Optional, Tuple

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


def save_resume_and_extract_text(
    candidate_id: str,
    resume_id: str,
    content: bytes,
    content_type: str,
) -> Tuple[str, Optional[Path]]:
    """
    Save resume file to disk and extract text if PDF.
    Returns (extracted_text, file_path). file_path is None if save failed.
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
        return "", None
    text = ""
    if ext == "pdf":
        text = extract_text_from_pdf(content)
    return text, path
