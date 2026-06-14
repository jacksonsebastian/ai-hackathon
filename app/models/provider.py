"""
Abstract Model Provider interface for LLM inference.

Defines the contract that all providers (Mock, vLLM, OpenAI) must implement.
This enables seamless switching between local dev (no GPU) and GPU environments.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Type, Any


@dataclass
class GenerationConfig:
    """Configuration for a single LLM generation call."""
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    stop: list[str] = field(default_factory=list)
    json_mode: bool = False
    stream: bool = False


@dataclass
class GenerationResult:
    """Result from an LLM generation call."""
    text: str
    model: str = ""
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str = ""


class ModelProvider(abc.ABC):
    """
    Abstract base class for LLM model providers.
    
    All AI inference goes through this interface, allowing:
    - MockProvider for local development without GPU
    - VLLMProvider for GPU-accelerated inference
    - OpenAICompatibleProvider for any OpenAI-compatible API
    """

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """Generate a complete response."""
        ...

    @abc.abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        config: Optional[GenerationConfig] = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response, yielding tokens."""
        ...

    @abc.abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str = "",
        output_schema: Optional[dict] = None,
        config: Optional[GenerationConfig] = None,
    ) -> dict:
        """Generate a structured JSON response."""
        ...

    @abc.abstractmethod
    def get_model_info(self) -> dict:
        """Return info about the current model."""
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available."""
        ...
