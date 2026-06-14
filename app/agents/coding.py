"""Coding Assessment Agent - Problem generation and code evaluation."""

from __future__ import annotations
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.prompts.system_prompts import CODING_SYSTEM_PROMPT
from app.prompts.templates import build_coding_evaluation_prompt
from app.services.ai_service import AIService


class CodingAgent(BaseAgent):
    AGENT_TYPE = "coding"
    AGENT_NAME = "Coding Assessor"

    def __init__(self, ai_service: Optional[AIService] = None, session_id: str = ""):
        super().__init__(ai_service, CODING_SYSTEM_PROMPT, session_id)

    async def generate_problem(
        self,
        candidate_profile: str,
        difficulty: str = "medium",
        category: str = "General",
    ) -> dict:
        prompt = f"""Generate a coding interview problem.

Candidate Profile:
{candidate_profile}

Difficulty: {difficulty}
Category: {category}

Respond with JSON:
{{
    "question": "Clear problem statement",
    "examples": [
        {{"input": "example input", "output": "expected output", "explanation": "why"}}
    ],
    "constraints": ["constraint1", "constraint2"],
    "hints": ["hint1", "hint2"],
    "difficulty": "{difficulty}",
    "category": "{category}",
    "expected_time_complexity": "O(...)",
    "expected_space_complexity": "O(...)"
}}"""
        return await self.think_structured(prompt)

    async def evaluate_code(
        self, problem: str, code: str, language: str = "python"
    ) -> dict:
        prompt = build_coding_evaluation_prompt(problem, code, language)
        return await self.think_structured(prompt)
