"""
LLM Question Generator — generates conversation-style questions from resume + JD.
Used when the candidate starts the interview: questions are generated live and
stored as curated_questions (project-based: 1 medium + 3 follow-ups, 2–3 hard).
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert technical interviewer. Given a candidate's resume text and job description (JD), generate conversation-style interview questions.

Rules:
- Generate questions ONLY about the candidate's projects and experience mentioned in the resume.
- For each distinct project/role (pick 1-2 from the resume): create 1 initial question (medium difficulty) then exactly 3 follow-up questions that dig into different aspects (e.g. technical decisions, challenges, impact, learnings). Of these 3 follow-ups, at least 2 must be hard difficulty, the rest medium.
- Order: first 1-2 questions should be medium (opening), then the last 2-3 questions must be hard (follow-ups).
- Each question must be conversational and open-ended (e.g. "Tell me about...", "How did you...", "What was the most challenging..."). No coding tasks.
- Output valid JSON only, no markdown or extra text. The JSON must be a single object with one key "questions" whose value is an array of question objects. Each question object must have exactly: "question_id" (string, e.g. "conv_1"), "prompt" (string), "difficulty" ("medium" or "hard"), "order" (integer, 1-based), "time_limit_sec" (integer, 180-300 for conversational)."""

USER_PROMPT_TEMPLATE = """Resume:
---
{resume_text}
---

Job Description:
---
{jd_text}
---

Generate the conversation-style questions as specified. Output only the JSON object with key "questions"."""


def _get_client():
    """Return OpenAI client (OpenAI or Azure)."""
    try:
        from openai import OpenAI
    except ImportError:
        return None
    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        return None
    kwargs = {"api_key": api_key}
    base = (settings.OPENAI_API_BASE or "").strip()
    if base:
        kwargs["base_url"] = base
    return OpenAI(**kwargs)


def generate_conversation_questions(
    resume_text: str,
    jd_text: str,
    template_id: str,
    candidate_id: str,
) -> Optional[dict]:
    """
    Call LLM to generate conversation questions from resume + JD.
    Returns a curated_questions payload (template_id, generated_from, generated_at, generation_method, questions)
    or None if LLM is not configured or generation fails.
    """
    client = _get_client()
    if not client:
        logger.warning("OPENAI_API_KEY not set; skipping LLM question generation")
        return None
    model = (settings.OPENAI_MODEL or "gpt-4o-mini").strip() or "gpt-4o-mini"
    resume_text = (resume_text or "").strip() or "(No resume text provided)"
    jd_text = (jd_text or "").strip() or "(No job description provided)"
    user_prompt = USER_PROMPT_TEMPLATE.format(resume_text=resume_text[:12000], jd_text=jd_text[:4000])
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
        )
        content = (response.choices[0].message.content or "").strip()
        if not content:
            return None
        # Parse JSON (handle optional markdown code block)
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(content)
        questions_raw = data.get("questions") or []
        questions = []
        for i, q in enumerate(questions_raw):
            if not isinstance(q, dict):
                continue
            q_id = str(q.get("question_id") or f"conv_{i+1}")
            prompt = str(q.get("prompt") or "").strip()
            if not prompt:
                continue
            difficulty = "medium" if (q.get("difficulty") or "").lower() != "hard" else "hard"
            order = int(q.get("order") or i + 1)
            time_limit = int(q.get("time_limit_sec") or 240)
            questions.append({
                "question_id": q_id,
                "question_type": "conversational",
                "order": order,
                "prompt": prompt,
                "difficulty": difficulty,
                "time_limit_sec": min(max(time_limit, 120), 600),
                "conversation_config": {
                    "follow_up_depth": 3,
                    "ai_model": model,
                    "evaluation_mode": "contextual",
                },
            })
        questions.sort(key=lambda x: x["order"])
        for i, q in enumerate(questions):
            q["order"] = i + 1
        return {
            "template_id": template_id,
            "generated_from": {"resume_id": candidate_id, "jd_text_snippet": jd_text[:200]},
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generation_method": "llm_live",
            "questions": questions,
        }
    except Exception as e:
        logger.exception("LLM question generation failed: %s", e)
        return None
