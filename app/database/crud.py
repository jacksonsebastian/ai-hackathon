"""
CRUD operations for the AI Interviewer database.
"""

import json
from typing import Optional

from app.database.connection import get_db
from app.database.models import (
    Resume, InterviewSession, Question, Answer,
    Evaluation, CodingSubmission, FeedbackReport, AgentLog,
)
from app.utils.helpers import generate_id, now_utc
from app.utils.logger import get_db_logger

logger = get_db_logger()


# ── Resume CRUD ──────────────────────────────────────────────

def create_resume(resume: Resume) -> Resume:
    if not resume.id:
        resume.id = generate_id()
    if not resume.created_at:
        resume.created_at = now_utc()
        resume.updated_at = resume.created_at
    with get_db() as conn:
        row = resume.to_db_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        conn.execute(f"INSERT INTO resumes ({cols}) VALUES ({placeholders})", list(row.values()))
    logger.info(f"Created resume: {resume.id} ({resume.candidate_name})")
    return resume


def get_resume(resume_id: str) -> Optional[Resume]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        return Resume.from_db_row(dict(row)) if row else None


def get_all_resumes() -> list[Resume]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM resumes ORDER BY created_at DESC").fetchall()
        return [Resume.from_db_row(dict(r)) for r in rows]


def delete_resume(resume_id: str) -> bool:
    with get_db() as conn:
        result = conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
        return result.rowcount > 0


# ── Interview Session CRUD ───────────────────────────────────

def create_session(session: InterviewSession) -> InterviewSession:
    if not session.id:
        session.id = generate_id()
    if not session.created_at:
        session.created_at = now_utc()
        session.updated_at = session.created_at
    with get_db() as conn:
        row = session.to_db_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        conn.execute(f"INSERT INTO interview_sessions ({cols}) VALUES ({placeholders})", list(row.values()))
    logger.info(f"Created session: {session.id} (type={session.session_type})")
    return session


def get_session(session_id: str) -> Optional[InterviewSession]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM interview_sessions WHERE id = ?", (session_id,)).fetchone()
        return InterviewSession.from_db_row(dict(row)) if row else None


def get_sessions_for_resume(resume_id: str) -> list[InterviewSession]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM interview_sessions WHERE resume_id = ? ORDER BY created_at DESC",
            (resume_id,)
        ).fetchall()
        return [InterviewSession.from_db_row(dict(r)) for r in rows]


def update_session_status(session_id: str, status: str, **kwargs) -> bool:
    updates = ["status = ?", "updated_at = ?"]
    values = [status, now_utc()]
    for key, val in kwargs.items():
        updates.append(f"{key} = ?")
        values.append(val)
    values.append(session_id)
    with get_db() as conn:
        result = conn.execute(
            f"UPDATE interview_sessions SET {', '.join(updates)} WHERE id = ?", values
        )
        return result.rowcount > 0


def get_all_sessions() -> list[InterviewSession]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM interview_sessions ORDER BY created_at DESC").fetchall()
        return [InterviewSession.from_db_row(dict(r)) for r in rows]


# ── Question CRUD ────────────────────────────────────────────

def create_question(question: Question) -> Question:
    if not question.id:
        question.id = generate_id()
    if not question.created_at:
        question.created_at = now_utc()
    with get_db() as conn:
        row = question.to_db_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        conn.execute(f"INSERT INTO questions ({cols}) VALUES ({placeholders})", list(row.values()))
    return question


def get_questions_for_session(session_id: str) -> list[Question]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM questions WHERE session_id = ? ORDER BY question_order",
            (session_id,)
        ).fetchall()
        return [Question.from_db_row(dict(r)) for r in rows]


# ── Answer CRUD ──────────────────────────────────────────────

def create_answer(answer: Answer) -> Answer:
    if not answer.id:
        answer.id = generate_id()
    answer.answer_length = len(answer.answer_text)
    if not answer.created_at:
        answer.created_at = now_utc()
    with get_db() as conn:
        row = answer.to_db_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        conn.execute(f"INSERT INTO answers ({cols}) VALUES ({placeholders})", list(row.values()))
    return answer


def get_answers_for_session(session_id: str) -> list[Answer]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM answers WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
        return [Answer.from_db_row(dict(r)) for r in rows]


# ── Evaluation CRUD ──────────────────────────────────────────

def create_evaluation(evaluation: Evaluation) -> Evaluation:
    if not evaluation.id:
        evaluation.id = generate_id()
    if not evaluation.created_at:
        evaluation.created_at = now_utc()
    # Compute composite score
    scores = [
        evaluation.technical_accuracy,
        evaluation.depth_of_understanding,
        evaluation.communication_clarity,
        evaluation.problem_solving,
    ]
    if evaluation.code_quality > 0:
        scores.append(evaluation.code_quality)
    evaluation.composite_score = round(sum(scores) / len(scores), 2) if scores else 0
    with get_db() as conn:
        row = evaluation.to_db_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        conn.execute(f"INSERT INTO evaluations ({cols}) VALUES ({placeholders})", list(row.values()))
    return evaluation


def get_evaluations_for_session(session_id: str) -> list[Evaluation]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM evaluations WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
        return [Evaluation.from_db_row(dict(r)) for r in rows]


# ── Coding Submission CRUD ───────────────────────────────────

def create_coding_submission(sub: CodingSubmission) -> CodingSubmission:
    if not sub.id:
        sub.id = generate_id()
    if not sub.created_at:
        sub.created_at = now_utc()
    with get_db() as conn:
        row = sub.to_db_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        conn.execute(f"INSERT INTO coding_submissions ({cols}) VALUES ({placeholders})", list(row.values()))
    return sub


# ── Feedback Report CRUD ─────────────────────────────────────

def create_feedback_report(report: FeedbackReport) -> FeedbackReport:
    if not report.id:
        report.id = generate_id()
    if not report.generated_at:
        report.generated_at = now_utc()
    with get_db() as conn:
        row = report.to_db_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        conn.execute(f"INSERT INTO feedback_reports ({cols}) VALUES ({placeholders})", list(row.values()))
    logger.info(f"Created feedback report for session: {report.session_id}")
    return report


def get_feedback_report(session_id: str) -> Optional[FeedbackReport]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM feedback_reports WHERE session_id = ?", (session_id,)
        ).fetchone()
        return FeedbackReport.from_db_row(dict(row)) if row else None


# ── Agent Log CRUD ───────────────────────────────────────────

def create_agent_log(log: AgentLog) -> AgentLog:
    if not log.id:
        log.id = generate_id()
    if not log.created_at:
        log.created_at = now_utc()
    with get_db() as conn:
        row = log.to_db_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        conn.execute(f"INSERT INTO agent_logs ({cols}) VALUES ({placeholders})", list(row.values()))
    return log


def get_agent_logs_for_session(session_id: str) -> list[AgentLog]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_logs WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
        return [AgentLog.from_db_row(dict(r)) for r in rows]


# ── Dashboard Stats ──────────────────────────────────────────

def get_dashboard_stats() -> dict:
    with get_db() as conn:
        total_resumes = conn.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
        total_sessions = conn.execute("SELECT COUNT(*) FROM interview_sessions").fetchone()[0]
        completed = conn.execute(
            "SELECT COUNT(*) FROM interview_sessions WHERE status = 'completed'"
        ).fetchone()[0]
        avg_score_row = conn.execute(
            "SELECT AVG(overall_score) FROM feedback_reports"
        ).fetchone()
        avg_score = round(avg_score_row[0], 1) if avg_score_row[0] else 0
        return {
            "total_resumes": total_resumes,
            "total_sessions": total_sessions,
            "completed_sessions": completed,
            "in_progress": total_sessions - completed,
            "average_score": avg_score,
        }
