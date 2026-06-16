"""
SQLite database schema for the AI Interviewer Agent System.

Defines all 9 core tables and handles schema initialization.
Uses WAL journal mode for better concurrent access.
"""

import sqlite3
from pathlib import Path

from app.config import settings
from app.utils.logger import get_db_logger

logger = get_db_logger()

SCHEMA_SQL = """
-- ============================================================
-- RESUMES TABLE
-- Stores candidate information and parsed resume content
-- ============================================================
CREATE TABLE IF NOT EXISTS resumes (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK(file_type IN ('pdf', 'docx')),
    raw_text TEXT,
    candidate_name TEXT,
    email TEXT,
    phone TEXT,
    skills TEXT,              -- JSON array of skills
    experience TEXT,          -- JSON array of experience entries
    education TEXT,           -- JSON array of education entries
    projects TEXT,            -- JSON array of projects
    certifications TEXT,      -- JSON array of certifications
    technologies TEXT,        -- JSON array of technologies
    summary TEXT,             -- AI-generated candidate summary
    strengths TEXT,           -- JSON array of detected strengths
    gaps TEXT,                -- JSON array of detected gaps
    content_hash TEXT UNIQUE, -- For deduplication
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- INTERVIEW SESSIONS TABLE
-- Tracks each interview session lifecycle
-- ============================================================
CREATE TABLE IF NOT EXISTS interview_sessions (
    id TEXT PRIMARY KEY,
    resume_id TEXT NOT NULL,
    session_type TEXT NOT NULL DEFAULT 'full'
        CHECK(session_type IN ('full', 'technical', 'behavioral', 'coding')),
    status TEXT NOT NULL DEFAULT 'created'
        CHECK(status IN ('created', 'in_progress', 'paused', 'completed', 'cancelled')),
    current_agent TEXT,
    current_round TEXT,
    difficulty_level TEXT DEFAULT 'medium'
        CHECK(difficulty_level IN ('easy', 'medium', 'hard', 'adaptive')),
    total_questions INTEGER DEFAULT 0,
    total_answered INTEGER DEFAULT 0,
    overall_score REAL,
    config TEXT,              -- JSON: session-specific config overrides
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
);

-- ============================================================
-- QUESTIONS TABLE
-- All generated interview questions
-- ============================================================
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_type TEXT NOT NULL
        CHECK(agent_type IN ('technical', 'behavioral', 'coding', 'resume_analyzer', 'follow_up')),
    category TEXT,            -- e.g., 'DSA', 'System Design', 'React', 'Leadership'
    subcategory TEXT,         -- e.g., 'Arrays', 'Microservices', 'Hooks'
    question_text TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'medium'
        CHECK(difficulty IN ('easy', 'medium', 'hard')),
    expected_topics TEXT,     -- JSON: key topics the answer should cover
    max_score REAL DEFAULT 10.0,
    time_limit_seconds INTEGER,
    question_order INTEGER NOT NULL,
    is_follow_up INTEGER DEFAULT 0,
    parent_question_id TEXT,
    metadata TEXT,            -- JSON: additional question metadata
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_question_id) REFERENCES questions(id)
);

-- ============================================================
-- ANSWERS TABLE
-- Candidate responses to questions
-- ============================================================
CREATE TABLE IF NOT EXISTS answers (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    answer_length INTEGER,
    response_time_seconds REAL,
    confidence_score REAL,    -- AI-estimated confidence (0-1)
    completeness_score REAL,  -- How complete the answer is (0-1)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);

-- ============================================================
-- EVALUATIONS TABLE
-- Per-answer scoring with multi-dimensional rubric
-- ============================================================
CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT PRIMARY KEY,
    answer_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    technical_accuracy REAL DEFAULT 0 CHECK(technical_accuracy BETWEEN 0 AND 10),
    depth_of_understanding REAL DEFAULT 0 CHECK(depth_of_understanding BETWEEN 0 AND 10),
    communication_clarity REAL DEFAULT 0 CHECK(communication_clarity BETWEEN 0 AND 10),
    problem_solving REAL DEFAULT 0 CHECK(problem_solving BETWEEN 0 AND 10),
    code_quality REAL DEFAULT 0 CHECK(code_quality BETWEEN 0 AND 10),
    composite_score REAL DEFAULT 0 CHECK(composite_score BETWEEN 0 AND 10),
    reasoning TEXT,           -- LLM explanation for the scores
    key_strengths TEXT,       -- JSON array of answer strengths
    areas_to_improve TEXT,    -- JSON array of improvement areas
    evaluator_model TEXT,     -- Which model performed evaluation
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (answer_id) REFERENCES answers(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- ============================================================
-- CODING SUBMISSIONS TABLE
-- Code submissions for coding assessment rounds
-- ============================================================
CREATE TABLE IF NOT EXISTS coding_submissions (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'python',
    code_text TEXT NOT NULL,
    test_cases TEXT,          -- JSON: test case definitions
    test_results TEXT,        -- JSON: test execution results
    passed_tests INTEGER DEFAULT 0,
    total_tests INTEGER DEFAULT 0,
    time_complexity TEXT,
    space_complexity TEXT,
    code_quality_score REAL CHECK(code_quality_score BETWEEN 0 AND 10),
    feedback TEXT,            -- AI feedback on the code
    execution_time_ms REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);

-- ============================================================
-- EMBEDDINGS METADATA TABLE
-- Tracks vector embeddings stored in FAISS
-- ============================================================
CREATE TABLE IF NOT EXISTS embeddings_metadata (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL
        CHECK(source_type IN ('resume', 'knowledge_base', 'interview_qa', 'company_data')),
    source_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    chunk_text TEXT NOT NULL,
    chunk_hash TEXT,
    embedding_model TEXT NOT NULL,
    vector_dimension INTEGER NOT NULL,
    faiss_index_id INTEGER,   -- Position in FAISS index
    metadata TEXT,            -- JSON: additional metadata for filtering
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- FEEDBACK REPORTS TABLE
-- Final comprehensive interview reports
-- ============================================================
CREATE TABLE IF NOT EXISTS feedback_reports (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    resume_id TEXT NOT NULL,
    overall_score REAL CHECK(overall_score BETWEEN 0 AND 100),
    technical_score REAL CHECK(technical_score BETWEEN 0 AND 100),
    behavioral_score REAL CHECK(behavioral_score BETWEEN 0 AND 100),
    coding_score REAL CHECK(coding_score BETWEEN 0 AND 100),
    hiring_recommendation TEXT
        CHECK(hiring_recommendation IN ('strong_hire', 'hire', 'maybe', 'no_hire')),
    strengths TEXT,           -- JSON array
    weaknesses TEXT,          -- JSON array
    improvement_roadmap TEXT, -- JSON: structured improvement plan
    detailed_feedback TEXT,   -- Long-form AI-generated feedback
    summary TEXT,             -- Executive summary
    category_breakdown TEXT,  -- JSON: per-category score breakdown
    interviewer_notes TEXT,   -- JSON: per-agent observations
    report_version INTEGER DEFAULT 1,
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
);

-- ============================================================
-- INTERVIEW SNAPSHOTS TABLE
-- Webcam captures for integrity analysis
-- ============================================================
CREATE TABLE IF NOT EXISTS interview_snapshots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    candidate_id TEXT,
    captured_at TEXT NOT NULL DEFAULT (datetime('now')),
    question_number INTEGER,
    current_round TEXT,
    image_blob TEXT NOT NULL, -- Base64 encoded image
    image_format TEXT DEFAULT 'jpeg',
    analysis_json TEXT,       -- JSON: AI vision analysis results
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);

-- ============================================================
-- AGENT LOGS TABLE
-- Full audit trail of agent activity
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_logs (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    agent_name TEXT NOT NULL,
    action_type TEXT NOT NULL
        CHECK(action_type IN (
            'thinking', 'question_generated', 'answer_evaluated',
            'context_retrieved', 'delegation', 'tool_call',
            'error', 'state_change', 'memory_update'
        )),
    input_text TEXT,
    output_text TEXT,
    tokens_used INTEGER,
    latency_ms REAL,
    model_used TEXT,
    metadata TEXT,            -- JSON: action-specific data
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE SET NULL
);

-- ============================================================
-- INDEXES for query performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_sessions_resume ON interview_sessions(resume_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON interview_sessions(status);
CREATE INDEX IF NOT EXISTS idx_questions_session ON questions(session_id);
CREATE INDEX IF NOT EXISTS idx_questions_agent ON questions(agent_type);
CREATE INDEX IF NOT EXISTS idx_answers_session ON answers(session_id);
CREATE INDEX IF NOT EXISTS idx_answers_question ON answers(question_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_session ON evaluations(session_id);
CREATE INDEX IF NOT EXISTS idx_coding_session ON coding_submissions(session_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_source ON embeddings_metadata(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback_reports(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_session ON agent_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent ON agent_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_logs_time ON agent_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_session ON interview_snapshots(session_id);
"""


def init_db(db_path: str | None = None) -> None:
    """
    Initialize the SQLite database with the complete schema.
    
    Creates all tables, indexes, and enables WAL mode.
    Safe to call multiple times (uses IF NOT EXISTS).
    """
    path = db_path or settings.database.path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Initializing database at: {path}")
    
    conn = sqlite3.connect(path)
    try:
        # Enable WAL mode for better concurrency
        conn.execute(f"PRAGMA journal_mode={settings.database.journal_mode}")
        conn.execute("PRAGMA foreign_keys=ON")
        
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        
        # Verify tables were created
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Database initialized with {len(tables)} tables: {tables}")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        conn.close()


def get_schema_info() -> dict:
    """Return schema information for documentation/debugging."""
    return {
        "tables": [
            "resumes", "interview_sessions", "questions", "answers",
            "evaluations", "coding_submissions", "embeddings_metadata",
            "feedback_reports", "agent_logs", "interview_snapshots"
        ],
        "version": "1.0.0",
        "journal_mode": settings.database.journal_mode,
    }


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
