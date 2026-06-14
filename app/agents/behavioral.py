"""HR Behavioral Interview Agent."""

from __future__ import annotations
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.prompts.system_prompts import BEHAVIORAL_SYSTEM_PROMPT
from app.prompts.templates import build_question_prompt, build_evaluation_prompt
from app.services.ai_service import AIService


class BehavioralAgent(BaseAgent):
    AGENT_TYPE = "behavioral"
    AGENT_NAME = "Behavioral Interviewer"

    CATEGORIES = [
        "Leadership", "Teamwork", "Communication",
        "Problem Solving", "Adaptability", "Conflict Resolution",
    ]

    def __init__(self, ai_service: Optional[AIService] = None, session_id: str = ""):
        super().__init__(ai_service, BEHAVIORAL_SYSTEM_PROMPT, session_id)

    async def generate_question(
        self,
        candidate_profile: str,
        category: str = "",
        difficulty: str = "medium",
        previous_questions: list[str] | None = None,
        context: str = "",
    ) -> dict:
        prompt = build_question_prompt(
            agent_type="behavioral",
            candidate_profile=candidate_profile,
            category=category or "General Behavioral",
            difficulty=difficulty,
            previous_questions=previous_questions,
            context=context,
        )
        return await self.think_structured(prompt)

    async def evaluate_answer(
        self, question: str, answer: str, candidate_profile: str = ""
    ) -> dict:
        prompt = build_evaluation_prompt(question, answer, "behavioral", candidate_profile)
        return await self.think_structured(prompt)
