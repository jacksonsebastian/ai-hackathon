"""
Hybrid retriever combining dense (FAISS) and sparse (BM25) search.
"""

from __future__ import annotations

from typing import Optional

from app.rag.vector_store import get_vector_store, VectorStore
from app.config import settings
from app.utils.logger import get_rag_logger

logger = get_rag_logger()


class HybridRetriever:
    """
    Combines dense vector search (FAISS) with sparse keyword search (BM25)
    for better retrieval quality.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        alpha: float | None = None,
    ):
        self.vector_store = vector_store or get_vector_store()
        self.alpha = alpha if alpha is not None else settings.rag.hybrid_alpha
        self.bm25 = None
        self.bm25_corpus: list[dict] = []

    def build_bm25_index(self, documents: list[dict]):
        """Build BM25 index from documents."""
        try:
            from rank_bm25 import BM25Okapi
            tokenized = [doc["text"].lower().split() for doc in documents]
            self.bm25 = BM25Okapi(tokenized)
            self.bm25_corpus = documents
            logger.info(f"BM25 index built with {len(documents)} documents")
        except ImportError:
            logger.warning("rank_bm25 not installed, using dense-only retrieval")

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        source_filter: str | None = None,
    ) -> list[dict]:
        """
        Hybrid retrieval combining dense and sparse results.
        """
        k = top_k or settings.rag.retrieval_top_k

        # Dense retrieval via FAISS
        dense_results = self.vector_store.search(query, top_k=k * 2)

        # Apply source filter
        if source_filter:
            dense_results = [r for r in dense_results if r.get("source_type") == source_filter]

        # Sparse retrieval via BM25
        sparse_results = []
        if self.bm25 is not None:
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k * 2]
            for idx in top_indices:
                if idx < len(self.bm25_corpus) and scores[idx] > 0:
                    result = dict(self.bm25_corpus[idx])
                    result["score"] = float(scores[idx])
                    result["retrieval_type"] = "sparse"
                    sparse_results.append(result)

        # Combine with weighted scoring
        if sparse_results:
            combined = self._merge_results(dense_results, sparse_results)
        else:
            combined = dense_results

        # Return top-k
        return combined[:k]

    def _merge_results(
        self, dense: list[dict], sparse: list[dict]
    ) -> list[dict]:
        """Merge dense and sparse results with weighted scores."""
        seen_texts = {}

        # Normalize scores
        max_dense = max((r["score"] for r in dense), default=1.0) or 1.0
        max_sparse = max((r["score"] for r in sparse), default=1.0) or 1.0

        for r in dense:
            key = r["text"][:100]
            norm_score = r["score"] / max_dense
            seen_texts[key] = {
                **r,
                "combined_score": self.alpha * norm_score,
                "retrieval_type": "hybrid",
            }

        for r in sparse:
            key = r["text"][:100]
            norm_score = r["score"] / max_sparse
            if key in seen_texts:
                seen_texts[key]["combined_score"] += (1 - self.alpha) * norm_score
            else:
                seen_texts[key] = {
                    **r,
                    "combined_score": (1 - self.alpha) * norm_score,
                    "retrieval_type": "hybrid",
                }

        results = sorted(seen_texts.values(), key=lambda x: x["combined_score"], reverse=True)
        return results

    def format_context(self, results: list[dict], max_tokens: int = 2000) -> str:
        """Format retrieved results into context string for prompt injection."""
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4

        for r in results:
            text = r.get("text", "")
            if total_chars + len(text) > max_chars:
                break
            source = r.get("source_type", "unknown")
            score = r.get("combined_score", r.get("score", 0))
            context_parts.append(f"[Source: {source}, Relevance: {score:.2f}]\n{text}")
            total_chars += len(text)

        return "\n\n---\n\n".join(context_parts) if context_parts else ""
