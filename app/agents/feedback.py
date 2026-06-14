"""Feedback Agent - Generates comprehensive interview reports."""

from __future__ import annotations
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.prompts.system_prompts import FEEDBACK_SYSTEM_PROMPT
from app.prompts.templates import build_feedback_prompt
from app.services.ai_service import AIService


class FeedbackAgent(BaseAgent):
    AGENT_TYPE = "feedback"
    AGENT_NAME = "Feedback Generator"

    def __init__(self, ai_service: Optional[AIService] = None, session_id: str = ""):
        super().__init__(ai_service, FEEDBACK_SYSTEM_PROMPT, session_id)

    async def generate_report(
        self,
        candidate_profile: str,
        questions_answers: list[dict],
        evaluations: list[dict],
    ) -> dict:
        prompt = build_feedback_prompt(candidate_profile, questions_answers, evaluations)
        result = await self.think_structured(prompt)
        # Ensure required fields
        defaults = {
            "overall_score": 50,
            "technical_score": 50,
            "behavioral_score": 50,
            "coding_score": 50,
            "hiring_recommendation": "maybe",
            "strengths": [],
            "weaknesses": [],
            "improvement_roadmap": {},
            "summary": "Interview completed. See detailed feedback.",
            "detailed_feedback": "",
        }
        for key, default in defaults.items():
            if key not in result:
                result[key] = default
        return result
