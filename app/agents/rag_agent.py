"""RAG Retrieval Agent - Semantic search and context injection."""

from __future__ import annotations
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.prompts.system_prompts import RAG_AGENT_SYSTEM_PROMPT
from app.rag.retriever import HybridRetriever
from app.rag.vector_store import get_vector_store
from app.services.ai_service import AIService


class RAGAgent(BaseAgent):
    AGENT_TYPE = "rag"
    AGENT_NAME = "RAG Retrieval Agent"

    def __init__(self, ai_service: Optional[AIService] = None, session_id: str = ""):
        super().__init__(ai_service, RAG_AGENT_SYSTEM_PROMPT, session_id)
        self.retriever = HybridRetriever()

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str | None = None,
    ) -> str:
        results = self.retriever.retrieve(query, top_k=top_k, source_filter=source_filter)
        return self.retriever.format_context(results)

    def retrieve_resume_context(self, query: str, top_k: int = 3) -> str:
        return self.retrieve_context(query, top_k=top_k, source_filter="resume")

    def retrieve_knowledge_context(self, query: str, top_k: int = 5) -> str:
        return self.retrieve_context(query, top_k=top_k, source_filter="knowledge_base")

    async def enhance_question_with_context(
        self, question: str, candidate_profile: str
    ) -> dict:
        context = self.retrieve_context(f"{question} {candidate_profile}", top_k=3)
        prompt = f"""Given the following context and question, enhance the question with relevant context.

Original Question: {question}
Retrieved Context: {context}

Respond with JSON:
{{
    "enhanced_question": "improved question with context",
    "context_used": "brief summary of context applied",
    "relevance_score": 0.0-1.0
}}"""
        return await self.think_structured(prompt)
