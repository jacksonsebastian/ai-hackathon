"""
Model Router – Central routing layer for all AI model requests.

Routes every task to the correct remote cloud endpoint.
NO models are loaded locally. All inference happens on Jupyter Cloud GPU.

Architecture:
    Streamlit (local) → HTTP API → Jupyter Cloud → AI Model → Response → Streamlit

Endpoints:
    DeepSeek-R1   → vLLM OpenAI-compatible API (port 8000)
    Whisper V3    → Custom FastAPI endpoint      (port 8001)
    Kokoro TTS    → Custom FastAPI endpoint      (port 8002)
    BGE-M3        → Custom FastAPI endpoint      (port 8003)
"""

from __future__ import annotations

import os
import io
import yaml
import httpx
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings
from app.utils.logger import get_service_logger

logger = get_service_logger("model_router")

# ── Endpoint Configuration ────────────────────────────────────

@dataclass
class EndpointConfig:
    """Configuration for a remote model endpoint."""
    name: str
    url: str
    model_id: str = ""
    port: int = 0
    healthy: bool = False
    tasks: list[str] = field(default_factory=list)


class ModelRouter:
    """
    Central router that directs all AI tasks to the correct
    remote cloud endpoint. No local inference.

    Usage:
        router = ModelRouter()
        
        # LLM tasks
        result = await router.generate("Your prompt", task="technical_questions")
        
        # Speech-to-text
        transcript = await router.transcribe(audio_bytes)
        
        # Text-to-speech
        audio = await router.synthesize("Question text")
        
        # Embeddings
        vectors = await router.embed(["text1", "text2"])
    """

    def __init__(self):
        self._endpoints: dict[str, EndpointConfig] = {}
        self._routing: dict[str, str] = {}
        self._client = httpx.AsyncClient(timeout=120.0)
        self._load_config()

    def _load_config(self):
        """Load model configuration from models.yaml and environment."""
        # Load models.yaml if it exists
        yaml_path = Path("models.yaml")
        if yaml_path.exists():
            with open(yaml_path) as f:
                config = yaml.safe_load(f)
            if config and "routing" in config:
                self._routing = config["routing"]
            logger.info(f"Loaded model config from {yaml_path}")

        # Configure endpoints from environment variables
        self._endpoints["deepseek_r1"] = EndpointConfig(
            name="DeepSeek-R1",
            url=os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
            model_id=os.getenv("VLLM_MODEL", "deepseek-ai/DeepSeek-R1"),
            port=8000,
            tasks=["resume_analysis", "technical_questions", "coding_questions",
                   "follow_up_questions", "technical_evaluation", "candidate_scoring",
                   "hiring_recommendation", "final_report", "resume_screening"],
        )

        self._endpoints["whisper_large_v3"] = EndpointConfig(
            name="Whisper Large V3",
            url=os.getenv("WHISPER_API_URL", "http://localhost:8001"),
            model_id=os.getenv("WHISPER_MODEL", "openai/whisper-large-v3"),
            port=8001,
            tasks=["speech_to_text", "interview_transcription"],
        )

        self._endpoints["kokoro_tts"] = EndpointConfig(
            name="Kokoro TTS",
            url=os.getenv("KOKORO_API_URL", "http://localhost:8002"),
            model_id="hexgrad/Kokoro-82M",
            port=8002,
            tasks=["text_to_speech", "interview_voice", "spoken_questions", "spoken_feedback"],
        )

        self._endpoints["bge_m3"] = EndpointConfig(
            name="BGE-M3",
            url=os.getenv("EMBEDDING_API_URL", "http://localhost:8003"),
            model_id=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
            port=8003,
            tasks=["resume_embeddings", "semantic_search", "rag_retrieval"],
        )

        logger.info(f"ModelRouter initialized with {len(self._endpoints)} endpoints")

    def get_endpoint(self, task: str) -> EndpointConfig:
        """Get the endpoint for a given task."""
        model_key = self._routing.get(task)
        if model_key and model_key in self._endpoints:
            return self._endpoints[model_key]
        # Fallback: search by task in endpoint task lists
        for key, ep in self._endpoints.items():
            if task in ep.tasks:
                return ep
        # Default to DeepSeek-R1 for any unknown task
        return self._endpoints["deepseek_r1"]

    # ── Health Checks ─────────────────────────────────────────

    async def check_health(self) -> dict[str, dict]:
        """Check health of all remote endpoints."""
        results = {}
        for key, ep in self._endpoints.items():
            try:
                if key == "deepseek_r1":
                    resp = await self._client.get(f"{ep.url}/models")
                else:
                    resp = await self._client.get(f"{ep.url}/health")
                ep.healthy = resp.status_code == 200
                results[key] = {
                    "name": ep.name,
                    "url": ep.url,
                    "healthy": ep.healthy,
                    "status_code": resp.status_code,
                }
            except Exception as e:
                ep.healthy = False
                results[key] = {
                    "name": ep.name,
                    "url": ep.url,
                    "healthy": False,
                    "error": str(e),
                }
        return results

    async def check_endpoint(self, endpoint_key: str) -> bool:
        """Check if a specific endpoint is healthy."""
        ep = self._endpoints.get(endpoint_key)
        if not ep:
            return False
        try:
            if endpoint_key == "deepseek_r1":
                resp = await self._client.get(f"{ep.url}/models")
            else:
                resp = await self._client.get(f"{ep.url}/health")
            ep.healthy = resp.status_code == 200
            return ep.healthy
        except Exception:
            ep.healthy = False
            return False

    def get_status(self) -> dict[str, dict]:
        """Get current status of all endpoints (sync, uses cached health)."""
        return {
            key: {
                "name": ep.name,
                "model": ep.model_id,
                "url": ep.url,
                "healthy": ep.healthy,
            }
            for key, ep in self._endpoints.items()
        }

    # ── DeepSeek-R1 (LLM) ────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        task: str = "technical_questions",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:
        """
        Generate text using DeepSeek-R1 via vLLM OpenAI-compatible API.
        All LLM tasks route here.
        """
        ep = self.get_endpoint(task)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": ep.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        resp = await self._client.post(
            f"{ep.url}/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "text": data["choices"][0]["message"]["content"],
            "model": data.get("model", ep.model_id),
            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
            "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
            "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
        }

    # ── Whisper Large V3 (STT) ────────────────────────────────

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict:
        """
        Transcribe audio using Whisper Large V3 on cloud.
        Sends audio bytes to remote FastAPI endpoint.
        """
        ep = self._endpoints["whisper_large_v3"]
        
        files = {"audio": ("recording.wav", io.BytesIO(audio_bytes), "audio/wav")}
        params = {"language": language}

        resp = await self._client.post(
            f"{ep.url}/transcribe",
            files=files,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()  # {"text": "transcribed text", "duration": 5.2, ...}

    # ── Kokoro TTS ────────────────────────────────────────────

    async def synthesize(
        self,
        text: str,
        voice: str = "",
        speed: float = 1.0,
    ) -> bytes:
        """
        Generate speech audio using Kokoro TTS on cloud.
        Returns WAV audio bytes.
        """
        ep = self._endpoints["kokoro_tts"]
        voice = voice or os.getenv("KOKORO_VOICE", "af_heart")

        payload = {
            "text": text,
            "voice": voice,
            "speed": speed,
        }

        resp = await self._client.post(
            f"{ep.url}/synthesize",
            json=payload,
        )
        resp.raise_for_status()
        return resp.content  # Raw WAV bytes

    # ── BGE-M3 Embeddings ─────────────────────────────────────

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using BGE-M3 on cloud.
        Returns list of embedding vectors.
        """
        ep = self._endpoints["bge_m3"]

        payload = {"texts": texts}

        resp = await self._client.post(
            f"{ep.url}/embed",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["embeddings"]  # [[0.1, 0.2, ...], ...]

    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        results = await self.embed([text])
        return results[0]

    # ── Cleanup ───────────────────────────────────────────────

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# ── Singleton ─────────────────────────────────────────────────

_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get or create the global ModelRouter instance."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def reset_model_router():
    """Reset the router (e.g., after config change)."""
    global _router
    _router = None
