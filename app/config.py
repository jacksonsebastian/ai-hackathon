"""
Central configuration for the AI Interviewer Agent System.

Supports two environments:
- "local": No GPU, uses MockProvider for LLM calls
- "gpu": Jupyter GPU environment, uses vLLM for real inference

All settings can be overridden via environment variables or .env file.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


@dataclass
class DatabaseConfig:
    """SQLite database configuration."""
    path: str = str(PROJECT_ROOT / "data" / "interviews.db")
    echo: bool = False
    journal_mode: str = "WAL"  # Write-Ahead Logging for better concurrency


@dataclass
class VLLMConfig:
    """vLLM server configuration for GPU environment."""
    base_url: str = "http://localhost:8000/v1"
    model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    timeout: int = 120
    max_retries: int = 3


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""
    model_name: str = "BAAI/bge-base-en-v1.5"
    dimension: int = 768
    batch_size: int = 32
    normalize: bool = True
    device: str = "cpu"  # "cpu" for local, "cuda" or "rocm" for GPU


@dataclass
class FAISSConfig:
    """FAISS vector store configuration."""
    index_path: str = str(PROJECT_ROOT / "data" / "faiss_index")
    similarity_metric: str = "cosine"  # "cosine" | "l2" | "ip"
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
    hybrid_alpha: float = 0.7  # Weight for dense vs sparse (1.0 = all dense)
    knowledge_base_path: str = str(PROJECT_ROOT / "data" / "knowledge_base")


@dataclass 
class AgentConfig:
    """Multi-agent system configuration."""
    max_turns_per_round: int = 10
    max_total_questions: int = 20
    technical_question_count: int = 8
    behavioral_question_count: int = 5
    coding_question_count: int = 3
    difficulty_levels: list = field(default_factory=lambda: ["easy", "medium", "hard"])
    enable_adaptive_difficulty: bool = True
    agent_verbose: bool = True


@dataclass
class FineTuningConfig:
    """Fine-tuning pipeline configuration."""
    base_model: str = "Qwen/Qwen2.5-7B-Instruct"
    output_dir: str = str(PROJECT_ROOT / "data" / "fine_tuned_models")
    dataset_path: str = str(PROJECT_ROOT / "data" / "fine_tuning")
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list = field(default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"])
    learning_rate: float = 2e-4
    num_epochs: int = 3
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    max_seq_length: int = 2048
    use_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_compute_dtype: str = "bfloat16"


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
    
    Environment modes:
    - ENVIRONMENT="local" → Uses MockProvider, no GPU needed
    - ENVIRONMENT="gpu"   → Uses VLLMProvider, requires GPU + vLLM server
    """
    # Core environment settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "mock")  # "mock" | "vllm" | "openai"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    vllm: VLLMConfig = field(default_factory=VLLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    faiss: FAISSConfig = field(default_factory=FAISSConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    fine_tuning: FineTuningConfig = field(default_factory=FineTuningConfig)
    interview: InterviewConfig = field(default_factory=InterviewConfig)
    
    def __post_init__(self):
        """Apply environment variable overrides."""
        # Override vLLM settings from env
        if os.getenv("VLLM_BASE_URL"):
            self.vllm.base_url = os.getenv("VLLM_BASE_URL")
        if os.getenv("VLLM_MODEL"):
            self.vllm.model_name = os.getenv("VLLM_MODEL")
        
        # Override embedding settings from env
        if os.getenv("EMBEDDING_MODEL"):
            self.embedding.model_name = os.getenv("EMBEDDING_MODEL")
        if os.getenv("EMBEDDING_DEVICE"):
            self.embedding.device = os.getenv("EMBEDDING_DEVICE")
        
        # Override database path from env
        if os.getenv("DATABASE_PATH"):
            self.database.path = os.getenv("DATABASE_PATH")
        
        # Auto-detect environment
        if self.ENVIRONMENT == "gpu":
            self.MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "vllm")
            self.embedding.device = os.getenv("EMBEDDING_DEVICE", "cuda")
        
        # Ensure data directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create required directories if they don't exist."""
        dirs = [
            Path(self.database.path).parent,
            Path(self.faiss.index_path),
            Path(self.rag.knowledge_base_path),
            Path(self.fine_tuning.output_dir),
            Path(self.fine_tuning.dataset_path),
            PROJECT_ROOT / "data" / "sample_resumes",
            PROJECT_ROOT / "logs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    @property
    def is_gpu_environment(self) -> bool:
        """Check if running in GPU environment."""
        return self.ENVIRONMENT == "gpu"
    
    @property
    def is_local_environment(self) -> bool:
        """Check if running in local dev environment."""
        return self.ENVIRONMENT == "local"


# Singleton settings instance
settings = Settings()
