"""
Interview Conductor Agent - Controls overall interview flow.

Manages the multi-agent orchestration, deciding which agent
asks the next question and maintaining interview state.
Uses ConversationMemory for contextual follow-ups.
"""

from __future__ import annotations

from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.technical import TechnicalAgent
from app.agents.behavioral import BehavioralAgent
from app.agents.resume_analyzer import ResumeAnalyzerAgent
from app.agents.rag_agent import RAGAgent
from app.agents.coding import CodingAgent
from app.agents.evaluator import EvaluatorAgent
from app.agents.feedback import FeedbackAgent
from app.memory.conversation import ConversationMemory
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

        # Conversation memory for contextual follow-ups
        self.memory = ConversationMemory(max_history=20)

        # Interview state
        self.question_count = 0
        self.round_sequence = ["resume_analyzer", "technical", "behavioral", "coding"]
        self.current_round = self.round_sequence[0]
        self.round_index = 0
        self.questions_asked: list[str] = []
        self.evaluations: list[dict] = []
        self.qa_pairs: list[dict] = []
        
        # Per-round question tracking
        self.round_question_counts: dict[str, int] = {r: 0 for r in self.round_sequence}

    def get_current_agent(self) -> BaseAgent:
        """Get the agent for the current round."""
        agent_map = {
            "resume_analyzer": self.resume_analyzer,
            "technical": self.technical,
            "behavioral": self.behavioral,
            "coding": self.coding,
        }
        return agent_map.get(self.current_round, self.technical)

    def advance_round(self) -> str:
        """Move to the next interview round."""
        self.round_index += 1
        if self.round_index < len(self.round_sequence):
            self.current_round = self.round_sequence[self.round_index]
            # Reset round question count
            self.round_question_counts.setdefault(self.current_round, 0)
        else:
            self.current_round = "completed"
        self.logger.info(f"Advanced to round: {self.current_round}")
        return self.current_round

    def should_advance_round(self) -> bool:
        """Check if current round should end based on per-round question count."""
        if self.current_round == "completed":
            return False
            
        limits = {
            "resume_analyzer": 1,
            "technical": settings.agent.technical_question_count,
            "behavioral": settings.agent.behavioral_question_count,
            "coding": settings.agent.coding_question_count,
        }
        current_limit = limits.get(self.current_round, 5)
        round_count = self.round_question_counts.get(self.current_round, 0)
        return round_count >= current_limit

    def restore_state(
        self,
        questions_asked: list[str],
        qa_pairs: list[dict],
        evaluations: list[dict],
        current_round: str = "",
        round_index: int = 0,
    ):
        """Restore conductor state from database (for session persistence)."""
        self.questions_asked = questions_asked
        self.qa_pairs = qa_pairs
        self.evaluations = evaluations
        self.question_count = len(questions_asked)
        
        if current_round and current_round in self.round_sequence:
            self.current_round = current_round
            self.round_index = self.round_sequence.index(current_round)
        elif round_index < len(self.round_sequence):
            self.round_index = round_index
            self.current_round = self.round_sequence[round_index]
        
        # Rebuild per-round counts from qa_pairs
        for qa in qa_pairs:
            cat = qa.get("category", "technical")
            self.round_question_counts[cat] = self.round_question_counts.get(cat, 0) + 1
        
        # Rebuild conversation memory
        for qa in qa_pairs:
            self.memory.add_message("interviewer", qa.get("question", ""))
            self.memory.add_message("candidate", qa.get("answer", ""))
        
        self.logger.info(
            f"State restored: {self.question_count} questions, round={self.current_round}"
        )

    async def generate_next_question(self, candidate_profile: str, context: str = "") -> dict:
        """Generate the next interview question using the appropriate agent."""
        agent = self.get_current_agent()

        # Get conversation context for follow-ups
        conv_context = self.memory.get_context()

        # Get RAG context
        try:
            rag_context = self.rag_agent.retrieve_context(
                f"{self.current_round} {candidate_profile[:200]}",
                top_k=3,
            )
        except Exception:
            rag_context = ""
        
        combined_context = "\n".join(filter(None, [context, rag_context, conv_context]))

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
        
        # Track per-round count
        self.round_question_counts[self.current_round] = self.round_question_counts.get(self.current_round, 0) + 1
        
        # Update conversation memory
        self.memory.add_message("interviewer", question)
        self.memory.add_message("candidate", answer)
        
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
            "round_question_count": self.round_question_counts.get(self.current_round, 0),
        }
