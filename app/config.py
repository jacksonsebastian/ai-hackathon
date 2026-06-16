"""
Central configuration for the AI Interviewer Agent System.

Local machine = thin client (Streamlit UI only).
All AI models run on Jupyter Cloud GPU, accessed via remote HTTP endpoints.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


@dataclass
class DatabaseConfig:
    """SQLite database configuration."""
    path: str = str(PROJECT_ROOT / "data" / "interviews.db")
    echo: bool = False
    journal_mode: str = "WAL"


@dataclass
class VLLMConfig:
    """Remote vLLM endpoint for DeepSeek-R1 on Jupyter Cloud GPU."""
    base_url: str = "http://localhost:8000/v1"
    model_name: str = "deepseek-ai/DeepSeek-R1"
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    timeout: int = 120
    max_retries: int = 3


@dataclass
class EmbeddingConfig:
    """Remote BGE-M3 endpoint on Jupyter Cloud GPU."""
    model_name: str = "BAAI/bge-m3"
    dimension: int = 1024
    batch_size: int = 32
    normalize: bool = True
    api_url: str = "http://localhost:8003"


@dataclass
class FAISSConfig:
    """FAISS vector store configuration."""
    index_path: str = str(PROJECT_ROOT / "data" / "faiss_index")
    similarity_metric: str = "cosine"
    nprobe: int = 10
    top_k: int = 5


@dataclass
class RAGConfig:
    """RAG pipeline configuration."""
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    retrieval_top_k: int = 5
    rerank_top_k: int = 3
    hybrid_alpha: float = 0.7
    knowledge_base_path: str = str(PROJECT_ROOT / "data" / "knowledge_base")


@dataclass
class AgentConfig:
    """Multi-agent interview orchestration settings."""
    max_turns_per_round: int = 10
    max_total_questions: int = 20
    technical_question_count: int = 8
    behavioral_question_count: int = 5
    coding_question_count: int = 3
    difficulty_levels: list = field(default_factory=lambda: ["easy", "medium", "hard"])
    enable_adaptive_difficulty: bool = True


@dataclass
class InterviewConfig:
    """Interview session configuration."""
    session_timeout_minutes: int = 60
    max_answer_length: int = 5000
    min_answer_length: int = 10
    scoring_dimensions: list = field(default_factory=lambda: [
        "technical_accuracy",
        "depth_of_understanding",
        "communication_clarity",
        "problem_solving",
        "code_quality",
    ])
    score_range: tuple = (0, 10)


@dataclass
class Settings:
    """
    Master configuration for the AI Interviewer Agent System.

    Local machine = thin client (Streamlit UI).
    All inference routes to remote Jupyter Cloud GPU endpoints.

    Models:
      - DeepSeek-R1 → vLLM (port 8000)
      - Whisper V3  → FastAPI (port 8001)
      - Kokoro TTS  → FastAPI (port 8001)
      - BGE-M3      → FastAPI (port 8001)
    """
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "vllm")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    vllm: VLLMConfig = field(default_factory=VLLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    faiss: FAISSConfig = field(default_factory=FAISSConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    interview: InterviewConfig = field(default_factory=InterviewConfig)

    def __post_init__(self):
        """Apply environment variable overrides."""
        if os.getenv("VLLM_BASE_URL"):
            self.vllm.base_url = os.getenv("VLLM_BASE_URL")
        if os.getenv("VLLM_MODEL"):
            self.vllm.model_name = os.getenv("VLLM_MODEL")
        if os.getenv("EMBEDDING_MODEL"):
            self.embedding.model_name = os.getenv("EMBEDDING_MODEL")
        if os.getenv("EMBEDDING_API_URL"):
            self.embedding.api_url = os.getenv("EMBEDDING_API_URL")
        if os.getenv("DATABASE_PATH"):
            self.database.path = os.getenv("DATABASE_PATH")
            
        # Agent configuration overrides
        if os.getenv("MAX_TOTAL_QUESTIONS"):
            self.agent.max_total_questions = int(os.getenv("MAX_TOTAL_QUESTIONS"))
        if os.getenv("TECHNICAL_QUESTION_COUNT"):
            self.agent.technical_question_count = int(os.getenv("TECHNICAL_QUESTION_COUNT"))
        if os.getenv("BEHAVIORAL_QUESTION_COUNT"):
            self.agent.behavioral_question_count = int(os.getenv("BEHAVIORAL_QUESTION_COUNT"))
        if os.getenv("CODING_QUESTION_COUNT"):
            self.agent.coding_question_count = int(os.getenv("CODING_QUESTION_COUNT"))
        if os.getenv("ENABLE_ADAPTIVE_DIFFICULTY"):
            self.agent.enable_adaptive_difficulty = os.getenv("ENABLE_ADAPTIVE_DIFFICULTY").lower() == "true"
            
        self._ensure_directories()

    def _ensure_directories(self):
        """Create required directories if they don't exist."""
        dirs = [
            Path(self.database.path).parent,
            Path(self.faiss.index_path),
            Path(self.rag.knowledge_base_path),
            PROJECT_ROOT / "data" / "sample_resumes",
            PROJECT_ROOT / "logs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


# Singleton settings instance
settings = Settings()
