"""
OpenAI-compatible Model Provider.
Connects to any API that follows the OpenAI format.
"""
import time
import json
import httpx
from typing import AsyncIterator, Optional

from .provider import ModelProvider, GenerationConfig, GenerationResult

class OpenAICompatibleProvider(ModelProvider):
    def __init__(self, base_url: str, api_key: str, model_name: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0
        )

    async def generate(self, prompt: str, system_prompt: str = "", config: Optional[GenerationConfig] = None) -> GenerationResult:
        config = config or GenerationConfig()
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": False
        }
        
        if config.stop:
            payload["stop"] = config.stop
            
        if config.json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        response = await self.client.post(f"{self.base_url}/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        
        latency = (time.time() - start_time) * 1000
        choice = data["choices"][0]
        usage = data.get("usage", {})
        
        return GenerationResult(
            text=choice["message"]["content"],
            model=self.model_name,
            tokens_used=usage.get("total_tokens", 0),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency,
            finish_reason=choice.get("finish_reason", "")
        )

    async def generate_stream(self, prompt: str, system_prompt: str = "", config: Optional[GenerationConfig] = None) -> AsyncIterator[str]:
        config = config or GenerationConfig()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": True
        }
        if config.stop:
            payload["stop"] = config.stop
            
        async with self.client.stream("POST", f"{self.base_url}/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError):
                        continue

    async def generate_structured(self, prompt: str, system_prompt: str = "", output_schema: Optional[dict] = None, config: Optional[GenerationConfig] = None) -> dict:
        config = config or GenerationConfig()
        config.json_mode = True
        
        if output_schema and system_prompt:
            system_prompt += f"\n\nPlease ensure the output strictly follows this JSON schema:\n{json.dumps(output_schema)}"
            
        result = await self.generate(prompt, system_prompt, config)
        try:
            return json.loads(result.text)
        except json.JSONDecodeError:
            return {}

    def get_model_info(self) -> dict:
        return {
            "provider": "openai_compatible",
            "model": self.model_name,
            "base_url": self.base_url
        }

    async def health_check(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/models")
            return response.status_code == 200
        except Exception:
            return False
