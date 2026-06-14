"""
vLLM Model Provider for GPU-accelerated inference.

Connects to a local vLLM server via OpenAI-compatible API.
Only used in the Jupyter GPU environment.
"""

from __future__ import annotations

import json
import time
from typing import AsyncIterator, Optional

import httpx

from app.config import settings
from app.models.provider import ModelProvider, GenerationConfig, GenerationResult
from app.utils.helpers import extract_json_from_response
from app.utils.logger import setup_logger

logger = setup_logger("vllm_provider")


class VLLMProvider(ModelProvider):
    """
    vLLM provider connecting to a local vLLM server.
    
    Requires vLLM server running with OpenAI-compatible API:
        python -m vllm.entrypoints.openai.api_server \
            --model Qwen/Qwen2.5-7B-Instruct --port 8000
    """

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = (base_url or settings.vllm.base_url).rstrip("/")
        self.model_name = model_name or settings.vllm.model_name
        self.timeout = timeout or settings.vllm.timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        )
        self.call_count = 0
        logger.info(f"VLLMProvider initialized: {self.base_url} model={self.model_name}")

    def _build_messages(self, prompt: str, system_prompt: str) -> list[dict]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        cfg = config or GenerationConfig()
        self.call_count += 1
        start = time.time()

        payload = {
            "model": self.model_name,
            "messages": self._build_messages(prompt, system_prompt),
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "stream": False,
        }
        if cfg.stop:
            payload["stop"] = cfg.stop
        if cfg.json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            usage = data.get("usage", {})
            elapsed = (time.time() - start) * 1000

            return GenerationResult(
                text=choice["message"]["content"],
                model=data.get("model", self.model_name),
                tokens_used=usage.get("total_tokens", 0),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                latency_ms=elapsed,
                finish_reason=choice.get("finish_reason", ""),
            )
        except httpx.HTTPError as e:
            logger.error(f"vLLM API error: {e}")
            raise ConnectionError(f"vLLM server error: {e}") from e

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        config: Optional[GenerationConfig] = None,
    ) -> AsyncIterator[str]:
        cfg = config or GenerationConfig()
        self.call_count += 1

        payload = {
            "model": self.model_name,
            "messages": self._build_messages(prompt, system_prompt),
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "stream": True,
        }

        try:
            async with self.client.stream("POST", "/chat/completions", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except httpx.HTTPError as e:
            logger.error(f"vLLM streaming error: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str = "",
        output_schema: Optional[dict] = None,
        config: Optional[GenerationConfig] = None,
    ) -> dict:
        cfg = config or GenerationConfig(json_mode=True)
        cfg.json_mode = True

        enhanced_prompt = prompt
        if output_schema:
            schema_str = json.dumps(output_schema, indent=2)
            enhanced_prompt += f"\n\nRespond ONLY with valid JSON matching this schema:\n{schema_str}"

        result = await self.generate(enhanced_prompt, system_prompt, cfg)
        parsed = extract_json_from_response(result.text)
        if parsed is None:
            logger.warning("Failed to parse structured output, returning raw text")
            return {"raw_response": result.text}
        return parsed

    def get_model_info(self) -> dict:
        return {
            "provider": "vllm",
            "model": self.model_name,
            "base_url": self.base_url,
            "environment": "gpu",
            "gpu_required": True,
            "total_calls": self.call_count,
        }

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get("/models")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()
