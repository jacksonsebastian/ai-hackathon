"""
Central AI Service Layer.

Provides a unified interface over all model providers with:
- Auto provider selection based on environment
- Retry logic with exponential backoff
- Token budget tracking
- Structured output support
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

from app.config import settings
from app.models.provider import ModelProvider, GenerationConfig, GenerationResult
from app.models.mock_provider import MockProvider
from app.utils.logger import get_service_logger

logger = get_service_logger("ai_service")

_provider_instance: Optional[ModelProvider] = None


def get_provider() -> ModelProvider:
    """Get or create the active model provider based on settings."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_type = settings.MODEL_PROVIDER

    if provider_type == "vllm":
        from app.models.vllm_provider import VLLMProvider
        _provider_instance = VLLMProvider()
    elif provider_type == "openai":
        from app.models.vllm_provider import VLLMProvider
        _provider_instance = VLLMProvider()  # OpenAI-compatible
    else:
        _provider_instance = MockProvider()

    logger.info(f"AI Service initialized with provider: {provider_type}")
    return _provider_instance


def reset_provider():
    """Reset provider instance (useful for testing or switching)."""
    global _provider_instance
    _provider_instance = None


class AIService:
    """
    High-level AI service with retry logic, token tracking,
    and convenience methods for common operations.
    """

    def __init__(self, provider: Optional[ModelProvider] = None):
        self.provider = provider or get_provider()
        self.total_tokens = 0
        self.total_calls = 0

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        config: Optional[GenerationConfig] = None,
        max_retries: int = 3,
    ) -> GenerationResult:
        """Generate with automatic retry on failure."""
        last_error = None
        for attempt in range(max_retries):
            try:
                result = await self.provider.generate(prompt, system_prompt, config)
                self.total_tokens += result.tokens_used
                self.total_calls += 1
                return result
            except Exception as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning(f"Generation attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
        raise last_error

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        config: Optional[GenerationConfig] = None,
    ) -> AsyncIterator[str]:
        """Stream generation tokens."""
        self.total_calls += 1
        async for token in self.provider.generate_stream(prompt, system_prompt, config):
            yield token

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str = "",
        output_schema: Optional[dict] = None,
        config: Optional[GenerationConfig] = None,
        max_retries: int = 3,
    ) -> dict:
        """Generate structured JSON output with retry."""
        last_error = None
        for attempt in range(max_retries):
            try:
                result = await self.provider.generate_structured(
                    prompt, system_prompt, output_schema, config
                )
                self.total_calls += 1
                return result
            except Exception as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning(f"Structured gen attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(wait)
        raise last_error

    async def health_check(self) -> dict:
        """Check provider health and return status."""
        is_healthy = await self.provider.health_check()
        info = self.provider.get_model_info()
        return {
            "healthy": is_healthy,
            "provider_info": info,
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
        }
