"""
Data models for the AI Interviewer Agent System.

Pydantic-style dataclasses representing all database entities
with JSON serialization support.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Resume:
    """Parsed resume data model."""
    id: str
    filename: str
    file_type: str
    raw_text: str = ""
    candidate_name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    summary: str = ""
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    content_hash: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_db_row(self) -> dict:
        """Convert to a dict suitable for SQLite insertion."""
        d = asdict(self)
        for key in ("skills", "experience", "education", "projects",
                     "certifications", "technologies", "strengths", "gaps"):
            d[key] = json.dumps(d[key])
        return d

    @classmethod
    def from_db_row(cls, row: dict) -> Resume:
        """Create from a SQLite row dict."""
        data = dict(row)
        for key in ("skills", "experience", "education", "projects",
                     "certifications", "technologies", "strengths", "gaps"):
            if data.get(key) and isinstance(data[key], str):
                data[key] = json.loads(data[key])
        return cls(**data)

    def get_profile_text(self) -> str:
        """Generate a text summary of the candidate profile for prompts."""
        parts = [f"Candidate: {self.candidate_name}"]
        if self.skills:
            parts.append(f"Skills: {', '.join(self.skills[:20])}")
        if self.technologies:
            parts.append(f"Technologies: {', '.join(self.technologies[:15])}")
        if self.experience:
            exp_summary = "; ".join(
                f"{e.get('title', 'N/A')} at {e.get('company', 'N/A')}"
                for e in self.experience[:5]
            )
            parts.append(f"Experience: {exp_summary}")
        if self.education:
            edu_summary = "; ".join(
                f"{e.get('degree', 'N/A')} from {e.get('institution', 'N/A')}"
                for e in self.education[:3]
            )
            parts.append(f"Education: {edu_summary}")
        if self.projects:
            proj_summary = "; ".join(
                p.get("name", "N/A") for p in self.projects[:5]
            )
            parts.append(f"Projects: {proj_summary}")
        if self.summary:
            parts.append(f"Summary: {self.summary}")
        return "\n".join(parts)


@dataclass
class InterviewSession:
    """Interview session state model."""
    id: str
    resume_id: str
    session_type: str = "full"
    status: str = "created"
    current_agent: str = ""
    current_round: str = ""
    difficulty_level: str = "medium"
    total_questions: int = 0
    total_answered: int = 0
    overall_score: Optional[float] = None
    config: dict = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_db_row(self) -> dict:
        d = asdict(self)
        d["config"] = json.dumps(d["config"])
        return d

    @classmethod
    def from_db_row(cls, row: dict) -> InterviewSession:
        data = dict(row)
        if data.get("config") and isinstance(data["config"], str):
            data["config"] = json.loads(data["config"])
        return cls(**data)


@dataclass
class Question:
    """Interview question model."""
    id: str
    session_id: str
    agent_type: str
    question_text: str
    question_order: int
    category: str = ""
    subcategory: str = ""
    difficulty: str = "medium"
    expected_topics: list[str] = field(default_factory=list)
    max_score: float = 10.0
    time_limit_seconds: Optional[int] = None
    is_follow_up: bool = False
    parent_question_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: str = ""

    def to_db_row(self) -> dict:
        d = asdict(self)
        d["expected_topics"] = json.dumps(d["expected_topics"])
        d["metadata"] = json.dumps(d["metadata"])
        d["is_follow_up"] = int(d["is_follow_up"])
        return d

    @classmethod
    def from_db_row(cls, row: dict) -> Question:
        data = dict(row)
        for key in ("expected_topics", "metadata"):
            if data.get(key) and isinstance(data[key], str):
                data[key] = json.loads(data[key])
        data["is_follow_up"] = bool(data.get("is_follow_up", 0))
        return cls(**data)


@dataclass
class Answer:
    """Candidate answer model."""
    id: str
    question_id: str
    session_id: str
    answer_text: str
    answer_length: int = 0
    response_time_seconds: float = 0.0
    confidence_score: Optional[float] = None
    completeness_score: Optional[float] = None
    created_at: str = ""

    def to_db_row(self) -> dict:
        return asdict(self)

    @classmethod
    def from_db_row(cls, row: dict) -> Answer:
        return cls(**dict(row))


@dataclass
class Evaluation:
    """Per-answer evaluation with multi-dimensional scoring."""
    id: str
    answer_id: str
    session_id: str
    question_id: str
    technical_accuracy: float = 0.0
    depth_of_understanding: float = 0.0
    communication_clarity: float = 0.0
    problem_solving: float = 0.0
    code_quality: float = 0.0
    composite_score: float = 0.0
    reasoning: str = ""
    key_strengths: list[str] = field(default_factory=list)
    areas_to_improve: list[str] = field(default_factory=list)
    evaluator_model: str = ""
    created_at: str = ""

    def to_db_row(self) -> dict:
        d = asdict(self)
        d["key_strengths"] = json.dumps(d["key_strengths"])
        d["areas_to_improve"] = json.dumps(d["areas_to_improve"])
        return d

    @classmethod
    def from_db_row(cls, row: dict) -> Evaluation:
        data = dict(row)
        for key in ("key_strengths", "areas_to_improve"):
            if data.get(key) and isinstance(data[key], str):
                data[key] = json.loads(data[key])
        return cls(**data)


@dataclass
class CodingSubmission:
    """Code submission for coding assessment."""
    id: str
    question_id: str
    session_id: str
    code_text: str
    language: str = "python"
    test_cases: list[dict] = field(default_factory=list)
    test_results: list[dict] = field(default_factory=list)
    passed_tests: int = 0
    total_tests: int = 0
    time_complexity: str = ""
    space_complexity: str = ""
    code_quality_score: Optional[float] = None
    feedback: str = ""
    execution_time_ms: Optional[float] = None
    created_at: str = ""

    def to_db_row(self) -> dict:
        d = asdict(self)
        d["test_cases"] = json.dumps(d["test_cases"])
        d["test_results"] = json.dumps(d["test_results"])
        return d

    @classmethod
    def from_db_row(cls, row: dict) -> CodingSubmission:
        data = dict(row)
        for key in ("test_cases", "test_results"):
            if data.get(key) and isinstance(data[key], str):
                data[key] = json.loads(data[key])
        return cls(**data)


@dataclass
class FeedbackReport:
    """Final comprehensive interview feedback report."""
    id: str
    session_id: str
    resume_id: str
    overall_score: float = 0.0
    technical_score: float = 0.0
    behavioral_score: float = 0.0
    coding_score: float = 0.0
    hiring_recommendation: str = "maybe"
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    improvement_roadmap: dict = field(default_factory=dict)
    detailed_feedback: str = ""
    summary: str = ""
    category_breakdown: dict = field(default_factory=dict)
    interviewer_notes: dict = field(default_factory=dict)
    report_version: int = 1
    generated_at: str = ""

    def to_db_row(self) -> dict:
        d = asdict(self)
        for key in ("strengths", "weaknesses"):
            d[key] = json.dumps(d[key])
        for key in ("improvement_roadmap", "category_breakdown", "interviewer_notes"):
            d[key] = json.dumps(d[key])
        return d

    @classmethod
    def from_db_row(cls, row: dict) -> FeedbackReport:
        data = dict(row)
        for key in ("strengths", "weaknesses"):
            if data.get(key) and isinstance(data[key], str):
                data[key] = json.loads(data[key])
        for key in ("improvement_roadmap", "category_breakdown", "interviewer_notes"):
            if data.get(key) and isinstance(data[key], str):
                data[key] = json.loads(data[key])
        return cls(**data)


@dataclass
class AgentLog:
    """Agent activity log entry."""
    id: str
    agent_name: str
    action_type: str
    session_id: str = ""
    input_text: str = ""
    output_text: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    model_used: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: str = ""

    def to_db_row(self) -> dict:
        d = asdict(self)
        d["metadata"] = json.dumps(d["metadata"])
        return d

    @classmethod
    def from_db_row(cls, row: dict) -> AgentLog:
        data = dict(row)
        if data.get("metadata") and isinstance(data["metadata"], str):
            data["metadata"] = json.loads(data["metadata"])
        return cls(**data)
