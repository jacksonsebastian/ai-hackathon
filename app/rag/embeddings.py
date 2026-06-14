"""
Embedding pipeline for the RAG system.

Supports sentence-transformers models with fallback to mock embeddings
for local development without GPU.
"""

from __future__ import annotations

import hashlib
import json
import numpy as np
from pathlib import Path
from typing import Optional

from app.config import settings
from app.utils.logger import get_rag_logger

logger = get_rag_logger()

_model = None


def get_embedding_model():
    """Load the embedding model (lazy singleton)."""
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(
            settings.embedding.model_name,
            device=settings.embedding.device,
        )
        logger.info(f"Loaded embedding model: {settings.embedding.model_name}")
        return _model
    except ImportError:
        logger.warning("sentence-transformers not installed, using mock embeddings")
        return None
    except Exception as e:
        logger.warning(f"Failed to load embedding model: {e}, using mock embeddings")
        return None


def generate_mock_embedding(text: str, dim: int = 768) -> np.ndarray:
    """Generate a deterministic mock embedding from text hash."""
    h = hashlib.sha256(text.encode()).hexdigest()
    seed = int(h[:8], 16)
    rng = np.random.RandomState(seed)
    vec = rng.randn(dim).astype(np.float32)
    vec = vec / np.linalg.norm(vec)  # normalize
    return vec


def embed_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """
    Generate embeddings for a list of texts.
    Uses real model if available, otherwise mock embeddings.
    """
    model = get_embedding_model()

    if model is not None:
        logger.info(f"Embedding {len(texts)} texts with {settings.embedding.model_name}")
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 10,
            normalize_embeddings=settings.embedding.normalize,
        )
        return np.array(embeddings, dtype=np.float32)
    else:
        logger.info(f"Generating {len(texts)} mock embeddings (dim={settings.embedding.dimension})")
        return np.array(
            [generate_mock_embedding(t, settings.embedding.dimension) for t in texts],
            dtype=np.float32,
        )


def embed_single(text: str) -> np.ndarray:
    """Generate embedding for a single text."""
    return embed_texts([text])[0]
