"""Resume Analyzer Agent - Deep resume analysis and personalized questions."""

from __future__ import annotations
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.prompts.system_prompts import RESUME_ANALYZER_SYSTEM_PROMPT
from app.services.ai_service import AIService


class ResumeAnalyzerAgent(BaseAgent):
    AGENT_TYPE = "resume_analyzer"
    AGENT_NAME = "Resume Analyzer"

    def __init__(self, ai_service: Optional[AIService] = None, session_id: str = ""):
        super().__init__(ai_service, RESUME_ANALYZER_SYSTEM_PROMPT, session_id)

    async def analyze_resume(self, resume_text: str) -> dict:
        prompt = f"""Perform a deep analysis of this resume and generate personalized interview questions.

Resume:
{resume_text[:3000]}

Respond with JSON:
{{
    "profile_summary": "2-3 sentence summary",
    "key_strengths": ["strength1", "strength2", "strength3"],
    "potential_gaps": ["gap1", "gap2"],
    "experience_level": "junior|mid|senior",
    "recommended_topics": ["topic1", "topic2", "topic3"],
    "personalized_questions": [
        {{"question": "Q based on resume", "category": "category", "reason": "why this question"}},
        {{"question": "Q2", "category": "category", "reason": "reason"}},
        {{"question": "Q3", "category": "category", "reason": "reason"}}
    ],
    "difficulty_recommendation": "easy|medium|hard"
}}"""
        return await self.think_structured(prompt)

    async def detect_gaps(self, resume_text: str, job_requirements: str = "") -> dict:
        prompt = f"""Identify gaps between this resume and typical job requirements.

Resume:
{resume_text[:2000]}

{f"Job Requirements: {job_requirements}" if job_requirements else ""}

Respond with JSON:
{{
    "skill_gaps": ["gap1", "gap2"],
    "experience_gaps": ["gap1"],
    "questions_to_probe": ["question about gap1", "question about gap2"]
}}"""
        return await self.think_structured(prompt)
