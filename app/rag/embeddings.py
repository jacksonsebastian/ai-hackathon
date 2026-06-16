"""
Embedding pipeline for the RAG system.

Calls remote BGE-M3 endpoint on Jupyter Cloud GPU.
NO models loaded locally. All embedding computation happens on the cloud.

Flow: text → HTTP POST → Cloud BGE-M3 → embedding vector
"""

from __future__ import annotations

import os
import httpx
import numpy as np
from typing import Optional

from app.utils.logger import get_rag_logger

logger = get_rag_logger()

# Remote endpoint URL
_embedding_url = os.getenv("EMBEDDING_API_URL", "http://localhost:8003")
_embedding_dim = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    """Lazy-initialize HTTP client."""
    global _client
    if _client is None:
        _client = httpx.Client(timeout=60.0)
    return _client


def embed_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """
    Generate embeddings via remote BGE-M3 endpoint on cloud GPU.
    
    Sends texts over HTTP, receives embedding vectors.
    No local model loading.
    """
    if not texts:
        return np.array([], dtype=np.float32).reshape(0, _embedding_dim)
    
    client = _get_client()
    
    try:
        payload = {"texts": texts}
        resp = client.post(f"{_embedding_url}/embed", json=payload)
        resp.raise_for_status()
        data = resp.json()
        
        embeddings = np.array(data["embeddings"], dtype=np.float32)
        logger.info(f"BGE-M3 embedded {len(texts)} texts via cloud (dim={embeddings.shape[1]})")
        return embeddings
        
    except httpx.ConnectError:
        logger.error(f"Cannot connect to embedding service at {_embedding_url}")
        logger.warning("Falling back to deterministic hash embeddings for offline mode")
        return _fallback_embeddings(texts)
    except Exception as e:
        logger.error(f"Embedding API error: {e}")
        return _fallback_embeddings(texts)


def embed_single(text: str) -> np.ndarray:
    """Generate embedding for a single text via remote BGE-M3."""
    result = embed_texts([text])
    return result[0] if len(result) > 0 else np.zeros(_embedding_dim, dtype=np.float32)


def _fallback_embeddings(texts: list[str]) -> np.ndarray:
    """
    Deterministic hash-based embeddings as offline fallback.
    Only used when the cloud BGE-M3 endpoint is unreachable.
    NOT suitable for production — just prevents crashes.
    """
    import hashlib
    embeddings = []
    for text in texts:
        h = hashlib.sha256(text.encode()).hexdigest()
        seed = int(h[:8], 16)
        rng = np.random.RandomState(seed)
        vec = rng.randn(_embedding_dim).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        embeddings.append(vec)
    logger.warning(f"Used fallback hash embeddings for {len(texts)} texts (cloud BGE-M3 unavailable)")
    return np.array(embeddings, dtype=np.float32)
