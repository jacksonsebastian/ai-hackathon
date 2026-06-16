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
        
        # Mathematically calculate scores from evaluations
        tech_scores = [ev.get("composite_score", 0) for qa, ev in zip(questions_answers, evaluations) if qa.get("category") == "technical"]
        behav_scores = [ev.get("composite_score", 0) for qa, ev in zip(questions_answers, evaluations) if qa.get("category") == "behavioral"]
        coding_scores = [ev.get("composite_score", 0) for qa, ev in zip(questions_answers, evaluations) if qa.get("category") == "coding"]
        
        # Convert from 10-point scale to 100-point scale
        technical_score = int((sum(tech_scores) / max(len(tech_scores), 1)) * 10)
        behavioral_score = int((sum(behav_scores) / max(len(behav_scores), 1)) * 10)
        coding_score = int((sum(coding_scores) / max(len(coding_scores), 1)) * 10)
        
        all_scores = [ev.get("composite_score", 0) for ev in evaluations]
        overall_score = int((sum(all_scores) / max(len(all_scores), 1)) * 10)
        
        # Determine PASS/FAIL
        hiring_recommendation = "PASS" if overall_score >= 70 else "FAIL"

        # Ensure required fields
        defaults = {
            "overall_score": overall_score,
            "technical_score": technical_score,
            "behavioral_score": behavioral_score,
            "coding_score": coding_score,
            "hiring_recommendation": hiring_recommendation,
            "strengths": [],
            "weaknesses": [],
            "improvement_roadmap": {},
            "summary": "Interview completed. See detailed feedback.",
            "detailed_feedback": "",
        }
        for key, default in defaults.items():
            if key not in result:
                result[key] = default
                
        # Hard override the scores and recommendation from the LLM to ensure mathematical accuracy
        result["overall_score"] = overall_score
        result["technical_score"] = technical_score
        result["behavioral_score"] = behavioral_score
        result["coding_score"] = coding_score
        result["hiring_recommendation"] = hiring_recommendation
        
        return result
