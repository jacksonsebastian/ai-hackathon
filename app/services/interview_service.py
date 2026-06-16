"""
Interview orchestration service.
Manages the lifecycle of an interview session, coordinating between
the ConductorAgent and the database.

Supports session persistence via conductor rehydration from DB.
"""

from __future__ import annotations

from typing import Optional

from app.database import crud
from app.database.models import InterviewSession, Question, Answer
from app.agents.conductor import ConductorAgent
from app.services.ai_service import AIService
from app.utils.helpers import generate_id, now_utc
from app.utils.logger import get_service_logger

logger = get_service_logger("interview_service")


class InterviewService:
    """Core service for managing interview sessions."""

    def __init__(self, ai_service: Optional[AIService] = None):
        self.ai_service = ai_service or AIService()
        self.active_conductors: dict[str, ConductorAgent] = {}

    def start_session(self, resume_id: str, session_type: str = "full") -> InterviewSession:
        """Create and start a new interview session."""
        session = InterviewSession(
            id=generate_id(),
            resume_id=resume_id,
            session_type=session_type,
            status="in_progress",
            started_at=now_utc(),
        )
        crud.create_session(session)
        logger.info(f"Started new interview session {session.id} for resume {resume_id}")
        return session

    def get_conductor(self, session_id: str) -> ConductorAgent:
        """Get or initialize the conductor agent for a session. Rehydrates from DB if needed."""
        if session_id not in self.active_conductors:
            conductor = ConductorAgent(self.ai_service, session_id)
            
            # Rehydrate state from database
            self._rehydrate_conductor(conductor, session_id)
            
            self.active_conductors[session_id] = conductor
        return self.active_conductors[session_id]

    def _rehydrate_conductor(self, conductor: ConductorAgent, session_id: str):
        """Restore conductor state from database for session persistence."""
        try:
            session = crud.get_session(session_id)
            if not session:
                return
            
            questions = crud.get_questions_for_session(session_id)
            answers = crud.get_answers_for_session(session_id)
            evaluations = crud.get_evaluations_for_session(session_id)
            
            if not questions:
                return  # Fresh session, nothing to restore
            
            # Build Q&A pairs
            answer_map = {a.question_id: a for a in answers}
            questions_asked = []
            qa_pairs = []
            
            for q in questions:
                questions_asked.append(q.question_text)
                answer = answer_map.get(q.id)
                if answer:
                    qa_pairs.append({
                        "question": q.question_text,
                        "answer": answer.answer_text,
                        "category": q.agent_type,
                    })
            
            eval_dicts = []
            for ev in evaluations:
                eval_dicts.append({
                    "technical_accuracy": ev.technical_accuracy,
                    "depth_of_understanding": ev.depth_of_understanding,
                    "communication_clarity": ev.communication_clarity,
                    "problem_solving": ev.problem_solving,
                    "code_quality": ev.code_quality,
                    "composite_score": ev.composite_score,
                    "reasoning": ev.reasoning,
                    "key_strengths": ev.key_strengths,
                    "areas_to_improve": ev.areas_to_improve,
                })
            
            # Determine current round from session
            current_round = session.current_round or ""
            
            conductor.restore_state(
                questions_asked=questions_asked,
                qa_pairs=qa_pairs,
                evaluations=eval_dicts,
                current_round=current_round,
            )
            
            logger.info(f"Rehydrated conductor for session {session_id}: {len(questions_asked)} questions")
            
        except Exception as e:
            logger.warning(f"Failed to rehydrate conductor for {session_id}: {e}")

    async def get_next_question(self, session_id: str, candidate_profile: str) -> Question:
        """Generate the next question using the conductor."""
        conductor = self.get_conductor(session_id)
        
        if conductor.should_advance_round():
            conductor.advance_round()
            
        crud.update_session_status(
            session_id, 
            status="in_progress", 
            current_round=conductor.current_round
        )

        q_data = await conductor.generate_next_question(candidate_profile)
        
        # Sanitize agent_type to satisfy SQLite CHECK constraint
        agent_type = conductor.current_round
        allowed_types = ["technical", "behavioral", "coding", "resume_analyzer", "follow_up"]
        if agent_type not in allowed_types:
            agent_type = "follow_up"
        
        question = Question(
            id=generate_id(),
            session_id=session_id,
            agent_type=agent_type,
            category=q_data.get("category", ""),
            question_text=q_data.get("question", "Could you tell me more about your experience?"),
            difficulty=q_data.get("difficulty", "medium"),
            expected_topics=q_data.get("expected_topics", []),
            question_order=conductor.question_count + 1
        )
        crud.create_question(question)
        return question

    async def submit_answer(
        self, session_id: str, question_id: str, answer_text: str, candidate_profile: str
    ) -> dict:
        """Process a candidate's answer and run evaluation."""
        conductor = self.get_conductor(session_id)
        
        answer = Answer(
            id=generate_id(),
            question_id=question_id,
            session_id=session_id,
            answer_text=answer_text
        )
        crud.create_answer(answer)
        
        question = next((q for q in crud.get_questions_for_session(session_id) if q.id == question_id), None)
        q_text = question.question_text if question else "Unknown question"

        # Evaluate with DeepSeek-R1
        eval_result = await conductor.evaluate_answer(q_text, answer_text, candidate_profile)
        
        from app.database.models import Evaluation
        evaluation = Evaluation(
            id=generate_id(),
            answer_id=answer.id,
            session_id=session_id,
            question_id=question_id,
            technical_accuracy=eval_result.get("technical_accuracy", 0),
            depth_of_understanding=eval_result.get("depth_of_understanding", 0),
            communication_clarity=eval_result.get("communication_clarity", 0),
            problem_solving=eval_result.get("problem_solving", 0),
            code_quality=eval_result.get("code_quality", 0),
            reasoning=eval_result.get("reasoning", ""),
            key_strengths=eval_result.get("key_strengths", []),
            areas_to_improve=eval_result.get("areas_to_improve", [])
        )
        crud.create_evaluation(evaluation)
        
        # Update session progress
        crud.update_session_status(
            session_id,
            status="in_progress",
            total_answered=conductor.question_count,
            current_round=conductor.current_round,
        )
        
        return eval_result

    async def end_session(self, session_id: str, candidate_profile: str) -> dict:
        """End the session and generate the final report."""
        conductor = self.get_conductor(session_id)
        crud.update_session_status(session_id, status="completed", completed_at=now_utc())
        
        report_data = await conductor.generate_final_report(candidate_profile)
        
        from app.database.models import FeedbackReport
        report = FeedbackReport(
            id=generate_id(),
            session_id=session_id,
            resume_id=crud.get_session(session_id).resume_id,
            overall_score=report_data.get("overall_score", 0),
            technical_score=report_data.get("technical_score", 0),
            behavioral_score=report_data.get("behavioral_score", 0),
            coding_score=report_data.get("coding_score", 0),
            hiring_recommendation=report_data.get("hiring_recommendation", "maybe"),
            strengths=report_data.get("strengths", []),
            weaknesses=report_data.get("weaknesses", []),
            improvement_roadmap=report_data.get("improvement_roadmap", {}),
            summary=report_data.get("summary", ""),
            detailed_feedback=report_data.get("detailed_feedback", "")
        )
        crud.create_feedback_report(report)
        
        # Cleanup
        if session_id in self.active_conductors:
            del self.active_conductors[session_id]
            
        return report_data
