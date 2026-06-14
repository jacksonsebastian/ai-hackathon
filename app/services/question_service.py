"""
Question Generation Service.
Provides logic for dynamically generating and refining questions outside
the core interview loop, such as for practice modes or specific topic drilling.
"""

from __future__ import annotations

from typing import Optional

from app.services.ai_service import AIService
from app.prompts.templates import build_question_prompt
from app.utils.logger import get_service_logger

logger = get_service_logger("question_service")


class QuestionService:
    """Service for generating standalone practice questions."""

    def __init__(self, ai_service: Optional[AIService] = None):
        self.ai_service = ai_service or AIService()

    async def generate_practice_question(
        self,
        category: str,
        difficulty: str = "medium",
        context: str = ""
    ) -> dict:
        """Generate a practice question for a specific category."""
        prompt = build_question_prompt(
            agent_type="technical",  # defaults to technical for practice
            candidate_profile="Practice Candidate (general experience)",
            category=category,
            difficulty=difficulty,
            context=context,
        )
        
        logger.info(f"Generating practice question: {category} ({difficulty})")
        return await self.ai_service.generate_structured(
            prompt=prompt,
            system_prompt="You are an expert technical interviewer creating practice questions."
        )

    async def generate_follow_up(
        self,
        original_question: str,
        candidate_answer: str,
        category: str
    ) -> dict:
        """Generate a follow-up question based on the candidate's answer."""
        prompt = f"""Generate a follow-up question based on the candidate's answer.
        
Original Question ({category}): {original_question}
Candidate's Answer: {candidate_answer}

Requirements:
- The follow-up should probe deeper into areas the candidate glossed over
- Or it should ask them to apply their concept to a new edge case
- Keep it concise and conversational

Respond with JSON:
{{
    "question": "The follow-up question text",
    "reasoning": "Why this follow-up is relevant",
    "expected_topics": ["topic1"]
}}"""
        return await self.ai_service.generate_structured(
            prompt=prompt,
            system_prompt="You are an expert interviewer drilling deeper into a candidate's response."
        )
