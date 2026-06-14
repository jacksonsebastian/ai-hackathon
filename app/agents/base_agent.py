"""
Base agent class for the multi-agent interview system.

Provides shared functionality: memory access, logging, token tracking,
and the LLM generation interface.
"""

from __future__ import annotations

import time
from typing import Optional

from app.database.models import AgentLog
from app.database import crud
from app.models.provider import GenerationConfig, GenerationResult
from app.services.ai_service import AIService
from app.utils.helpers import generate_id, now_utc
from app.utils.logger import get_agent_logger


class BaseAgent:
    """Base class for all interview agents."""

    AGENT_TYPE: str = "base"
    AGENT_NAME: str = "Base Agent"

    def __init__(
        self,
        ai_service: Optional[AIService] = None,
        system_prompt: str = "",
        session_id: str = "",
    ):
        self.ai_service = ai_service or AIService()
        self.system_prompt = system_prompt
        self.session_id = session_id
        self.logger = get_agent_logger(self.AGENT_NAME)
        self.call_count = 0
        self.total_tokens = 0

    async def think(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """Core LLM call with logging and tracking."""
        self.call_count += 1
        start = time.time()

        result = await self.ai_service.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            config=config,
        )

        elapsed_ms = (time.time() - start) * 1000
        self.total_tokens += result.tokens_used

        # Log agent activity
        log = AgentLog(
            id=generate_id(),
            session_id=self.session_id,
            agent_name=self.AGENT_NAME,
            action_type="thinking",
            input_text=prompt[:500],
            output_text=result.text[:500],
            tokens_used=result.tokens_used,
            latency_ms=elapsed_ms,
            model_used=result.model,
            created_at=now_utc(),
        )
        try:
            crud.create_agent_log(log)
        except Exception as e:
            self.logger.warning(f"Failed to log agent activity: {e}")

        self.logger.info(
            f"Generated response ({result.tokens_used} tokens, {elapsed_ms:.0f}ms)"
        )
        return result

    async def think_structured(
        self,
        prompt: str,
        output_schema: Optional[dict] = None,
        config: Optional[GenerationConfig] = None,
    ) -> dict:
        """Structured JSON output with logging."""
        self.call_count += 1
        start = time.time()

        result = await self.ai_service.generate_structured(
            prompt=prompt,
            system_prompt=self.system_prompt,
            output_schema=output_schema,
            config=config,
        )

        elapsed_ms = (time.time() - start) * 1000

        log = AgentLog(
            id=generate_id(),
            session_id=self.session_id,
            agent_name=self.AGENT_NAME,
            action_type="thinking",
            input_text=prompt[:500],
            output_text=str(result)[:500],
            latency_ms=elapsed_ms,
            model_used="structured",
            created_at=now_utc(),
        )
        try:
            crud.create_agent_log(log)
        except Exception as e:
            self.logger.warning(f"Failed to log: {e}")

        return result

    def get_stats(self) -> dict:
        return {
            "agent_name": self.AGENT_NAME,
            "agent_type": self.AGENT_TYPE,
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
        }
