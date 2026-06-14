"""Evaluation Agent - Answer scoring with multi-dimensional rubrics."""

from __future__ import annotations
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.prompts.system_prompts import EVALUATOR_SYSTEM_PROMPT
from app.prompts.templates import build_evaluation_prompt
from app.services.ai_service import AIService


class EvaluatorAgent(BaseAgent):
    AGENT_TYPE = "evaluator"
    AGENT_NAME = "Answer Evaluator"

    def __init__(self, ai_service: Optional[AIService] = None, session_id: str = ""):
        super().__init__(ai_service, EVALUATOR_SYSTEM_PROMPT, session_id)

    async def evaluate(
        self,
        question: str,
        answer: str,
        agent_type: str = "technical",
        candidate_profile: str = "",
    ) -> dict:
        prompt = build_evaluation_prompt(question, answer, agent_type, candidate_profile)
        result = await self.think_structured(prompt)
        # Ensure all score fields exist with defaults
        defaults = {
            "technical_accuracy": 5.0,
            "depth_of_understanding": 5.0,
            "communication_clarity": 5.0,
            "problem_solving": 5.0,
            "code_quality": 0.0,
            "reasoning": "Evaluation completed",
            "key_strengths": [],
            "areas_to_improve": [],
        }
        for key, default in defaults.items():
            if key not in result:
                result[key] = default
        # Compute composite
        scores = [
            result["technical_accuracy"],
            result["depth_of_understanding"],
            result["communication_clarity"],
            result["problem_solving"],
        ]
        if result["code_quality"] > 0:
            scores.append(result["code_quality"])
        result["composite_score"] = round(sum(scores) / len(scores), 2)
        return result
