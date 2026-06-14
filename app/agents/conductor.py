"""
Interview Conductor Agent - Controls overall interview flow.

Manages the multi-agent orchestration, deciding which agent
asks the next question and maintaining interview state.
"""

from __future__ import annotations

import random
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.technical import TechnicalAgent
from app.agents.behavioral import BehavioralAgent
from app.agents.resume_analyzer import ResumeAnalyzerAgent
from app.agents.rag_agent import RAGAgent
from app.agents.coding import CodingAgent
from app.agents.evaluator import EvaluatorAgent
from app.agents.feedback import FeedbackAgent
from app.prompts.system_prompts import CONDUCTOR_SYSTEM_PROMPT
from app.config import settings
from app.services.ai_service import AIService


class ConductorAgent(BaseAgent):
    AGENT_TYPE = "conductor"
    AGENT_NAME = "Interview Conductor"

    def __init__(self, ai_service: Optional[AIService] = None, session_id: str = ""):
        super().__init__(ai_service, CONDUCTOR_SYSTEM_PROMPT, session_id)

        # Initialize all specialist agents
        self.technical = TechnicalAgent(ai_service, session_id)
        self.behavioral = BehavioralAgent(ai_service, session_id)
        self.resume_analyzer = ResumeAnalyzerAgent(ai_service, session_id)
        self.rag_agent = RAGAgent(ai_service, session_id)
        self.coding = CodingAgent(ai_service, session_id)
        self.evaluator = EvaluatorAgent(ai_service, session_id)
        self.feedback = FeedbackAgent(ai_service, session_id)

        # Interview state
        self.question_count = 0
        self.round_sequence = ["resume_analyzer", "technical", "behavioral", "coding", "feedback"]
        self.current_round = self.round_sequence[0]
        self.round_index = 0
        self.questions_asked: list[str] = []
        self.evaluations: list[dict] = []
        self.qa_pairs: list[dict] = []

    def get_current_agent(self) -> BaseAgent:
        """Get the agent for the current round."""
        agent_map = {
            "resume_analyzer": self.resume_analyzer,
            "technical": self.technical,
            "behavioral": self.behavioral,
            "coding": self.coding,
            "feedback": self.feedback,
        }
        return agent_map.get(self.current_round, self.technical)

    def advance_round(self) -> str:
        """Move to the next interview round."""
        self.round_index += 1
        if self.round_index < len(self.round_sequence):
            self.current_round = self.round_sequence[self.round_index]
        else:
            self.current_round = "completed"
        self.logger.info(f"Advanced to round: {self.current_round}")
        return self.current_round

    def should_advance_round(self) -> bool:
        """Check if current round should end."""
        limits = {
            "resume_analyzer": 1,
            "technical": settings.agent.technical_question_count,
            "behavioral": settings.agent.behavioral_question_count,
            "coding": settings.agent.coding_question_count,
        }
        current_limit = limits.get(self.current_round, 5)
        round_questions = sum(
            1 for q in self.questions_asked
            if True  # simplified; all questions count toward round
        )
        return self.question_count >= current_limit

    async def generate_next_question(self, candidate_profile: str, context: str = "") -> dict:
        """Generate the next interview question using the appropriate agent."""
        agent = self.get_current_agent()

        # Get RAG context
        rag_context = self.rag_agent.retrieve_context(
            f"{self.current_round} {candidate_profile[:200]}",
            top_k=3,
        )
        combined_context = f"{context}\n{rag_context}" if rag_context else context

        if self.current_round == "resume_analyzer":
            result = await self.resume_analyzer.analyze_resume(candidate_profile)
            if "personalized_questions" in result and result["personalized_questions"]:
                q = result["personalized_questions"][0]
                result["question"] = q.get("question", "Tell me about your experience.")
            return result

        elif self.current_round == "coding":
            return await self.coding.generate_problem(
                candidate_profile=candidate_profile,
                difficulty="medium",
            )

        elif self.current_round in ("technical", "behavioral"):
            gen_agent = self.technical if self.current_round == "technical" else self.behavioral
            return await gen_agent.generate_question(
                candidate_profile=candidate_profile,
                difficulty="medium",
                previous_questions=self.questions_asked[-5:],
                context=combined_context,
            )

        return {"question": "Thank you for completing the interview!"}

    async def evaluate_answer(
        self, question: str, answer: str, candidate_profile: str = ""
    ) -> dict:
        """Evaluate a candidate's answer."""
        result = await self.evaluator.evaluate(
            question=question,
            answer=answer,
            agent_type=self.current_round,
            candidate_profile=candidate_profile,
        )
        self.evaluations.append(result)
        self.qa_pairs.append({"question": question, "answer": answer, "category": self.current_round})
        self.question_count += 1
        self.questions_asked.append(question)
        return result

    async def generate_final_report(self, candidate_profile: str) -> dict:
        """Generate the final feedback report."""
        return await self.feedback.generate_report(
            candidate_profile=candidate_profile,
            questions_answers=self.qa_pairs,
            evaluations=self.evaluations,
        )

    def get_progress(self) -> dict:
        """Get current interview progress."""
        total = settings.agent.max_total_questions
        return {
            "current_round": self.current_round,
            "round_index": self.round_index,
            "total_rounds": len(self.round_sequence),
            "questions_asked": self.question_count,
            "total_questions": total,
            "progress_pct": min(100, int(self.question_count / max(total, 1) * 100)),
        }
