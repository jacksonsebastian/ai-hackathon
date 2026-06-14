"""Technical Interview Agent - DSA, System Design, Framework questions."""

from __future__ import annotations
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.prompts.system_prompts import TECHNICAL_SYSTEM_PROMPT
from app.prompts.templates import build_question_prompt, build_evaluation_prompt
from app.services.ai_service import AIService


class TechnicalAgent(BaseAgent):
    AGENT_TYPE = "technical"
    AGENT_NAME = "Technical Interviewer"

    CATEGORIES = [
        "DSA", "System Design", "React", "Node.js",
        "Database", "API Design", "Python", "DevOps",
    ]

    def __init__(self, ai_service: Optional[AIService] = None, session_id: str = ""):
        super().__init__(ai_service, TECHNICAL_SYSTEM_PROMPT, session_id)

    async def generate_question(
        self,
        candidate_profile: str,
        category: str = "",
        difficulty: str = "medium",
        previous_questions: list[str] | None = None,
        context: str = "",
    ) -> dict:
        prompt = build_question_prompt(
            agent_type="technical",
            candidate_profile=candidate_profile,
            category=category or "General Technical",
            difficulty=difficulty,
            previous_questions=previous_questions,
            context=context,
        )
        return await self.think_structured(prompt)

    async def evaluate_answer(
        self, question: str, answer: str, candidate_profile: str = ""
    ) -> dict:
        prompt = build_evaluation_prompt(question, answer, "technical", candidate_profile)
        return await self.think_structured(prompt)
