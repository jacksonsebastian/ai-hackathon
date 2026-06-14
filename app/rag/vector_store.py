"""
FAISS vector store wrapper for the RAG pipeline.
"""

from __future__ import annotations

import json
import pickle
import numpy as np
from pathlib import Path
from typing import Optional

from app.config import settings
from app.rag.chunking import Chunk
from app.rag.embeddings import embed_texts, embed_single
from app.utils.logger import get_rag_logger

logger = get_rag_logger()


class VectorStore:
    """FAISS-based vector store with metadata support."""

    def __init__(self, index_path: str | None = None, dimension: int | None = None):
        self.index_path = Path(index_path or settings.faiss.index_path)
        self.dimension = dimension or settings.embedding.dimension
        self.index = None
        self.metadata: list[dict] = []  # Parallel array to FAISS index
        self._faiss = None
        self._init_faiss()

    def _init_faiss(self):
        self._vectors = []
        try:
            import faiss
            self._faiss = faiss
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine with normalized vecs)
            logger.info(f"FAISS initialized (dim={self.dimension})")
        except ImportError:
            logger.warning("FAISS not installed. Using numpy fallback.")
            self._faiss = None

    def add(self, chunks: list[Chunk]) -> int:
        """Add chunks to the vector store, generating embeddings."""
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        embeddings = embed_texts(texts)

        for i, chunk in enumerate(chunks):
            self.metadata.append({
                "text": chunk.text,
                "source_id": chunk.source_id,
                "source_type": chunk.source_type,
                "chunk_index": chunk.index,
                **(chunk.metadata or {}),
            })

        if self._faiss and self.index is not None:
            self.index.add(embeddings)
        else:
            for emb in embeddings:
                self._vectors.append(emb)

        logger.info(f"Added {len(chunks)} chunks to vector store (total: {self.size})")
        return len(chunks)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search for similar chunks by query text."""
        query_embedding = embed_single(query).reshape(1, -1)

        if self._faiss and self.index is not None and self.index.ntotal > 0:
            k = min(top_k, self.index.ntotal)
            distances, indices = self.index.search(query_embedding, k)
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self.metadata):
                    result = dict(self.metadata[idx])
                    result["score"] = float(dist)
                    results.append(result)
            return results
        elif self._vectors:
            # Numpy fallback
            vectors = np.array(self._vectors, dtype=np.float32)
            similarities = np.dot(vectors, query_embedding.T).flatten()
            top_indices = np.argsort(similarities)[::-1][:top_k]
            results = []
            for idx in top_indices:
                if idx < len(self.metadata):
                    result = dict(self.metadata[idx])
                    result["score"] = float(similarities[idx])
                    results.append(result)
            return results
        return []

    @property
    def size(self) -> int:
        if self._faiss and self.index is not None:
            return self.index.ntotal
        return len(getattr(self, "_vectors", []))

    def save(self, path: str | None = None):
        """Persist the index and metadata to disk."""
        save_path = Path(path or self.index_path)
        save_path.mkdir(parents=True, exist_ok=True)

        if self._faiss and self.index is not None:
            import faiss
            faiss.write_index(self.index, str(save_path / "index.faiss"))

        with open(save_path / "metadata.pkl", "wb") as f:
            pickle.dump(self.metadata, f)

        logger.info(f"Vector store saved to {save_path} ({self.size} vectors)")

    def load(self, path: str | None = None) -> bool:
        """Load the index and metadata from disk."""
        load_path = Path(path or self.index_path)
        
        meta_path = load_path / "metadata.pkl"
        index_path = load_path / "index.faiss"

        if meta_path.exists():
            with open(meta_path, "rb") as f:
                self.metadata = pickle.load(f)

        if self._faiss and index_path.exists():
            import faiss
            self.index = faiss.read_index(str(index_path))
            logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            return True

        logger.warning("No saved index found")
        return False

    def clear(self):
        """Clear all vectors and metadata."""
        self._init_faiss()
        self.metadata = []
        if not self._faiss:
            self._vectors = []


# Singleton instance
_store: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
        _store.load()  # Try to load existing index
    return _store
