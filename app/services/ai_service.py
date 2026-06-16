"""
Central AI Service Layer.

Routes ALL inference to remote cloud endpoints via ModelRouter.
NO models are loaded locally. All calls go over HTTP.

Flow: Streamlit → AIService → ModelRouter → Cloud GPU → Response
"""

from __future__ import annotations

import asyncio
import re
from typing import AsyncIterator, Optional

from app.models.model_router import get_model_router
from app.models.provider import ModelProvider, GenerationConfig, GenerationResult
from app.utils.helpers import extract_json_from_response
from app.utils.logger import get_service_logger

logger = get_service_logger("ai_service")

_provider_instance: Optional[ModelProvider] = None


def _strip_think_tags(text: str) -> str:
    """Strip DeepSeek-R1 <think>...</think> reasoning tags, keeping only the final answer."""
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()


def get_provider() -> ModelProvider:
    """Get or create the vLLM model provider (remote DeepSeek-R1)."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    from app.models.vllm_provider import VLLMProvider
    _provider_instance = VLLMProvider()

    logger.info(f"AI Service initialized — connecting to remote vLLM endpoint")
    return _provider_instance


def reset_provider():
    """Reset provider instance (useful for config changes)."""
    global _provider_instance
    _provider_instance = None


class AIService:
    """
    High-level AI service with retry logic, token tracking,
    and convenience methods for common operations.
    
    All calls are routed to remote cloud endpoints.
    No local model loading or inference.
    """

    def __init__(self, provider: Optional[ModelProvider] = None):
        self.provider = provider or get_provider()
        self.router = get_model_router()
        self.total_tokens = 0
        self.total_calls = 0

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        config: Optional[GenerationConfig] = None,
        max_retries: int = 3,
    ) -> GenerationResult:
        """Generate with automatic retry on failure. Routes to remote DeepSeek-R1."""
        last_error = None
        for attempt in range(max_retries):
            try:
                result = await self.provider.generate(prompt, system_prompt, config)
                self.total_tokens += result.tokens_used
                self.total_calls += 1
                # Strip DeepSeek-R1 think tags
                result.text = _strip_think_tags(result.text)
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
        """Stream generation tokens from remote DeepSeek-R1."""
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
        """Generate structured JSON output with retry. Routes to remote DeepSeek-R1."""
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
        """Check all remote endpoint health via ModelRouter."""
        provider_healthy = await self.provider.health_check()
        router_health = await self.router.check_health()
        info = self.provider.get_model_info()
        return {
            "provider_healthy": provider_healthy,
            "provider_info": info,
            "endpoints": router_health,
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
        }
