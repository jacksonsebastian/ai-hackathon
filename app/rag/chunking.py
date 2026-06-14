"""
Document chunking strategies for the RAG pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
    """A text chunk with metadata."""
    text: str
    index: int
    source_id: str
    source_type: str
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def recursive_character_split(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    separators: list[str] | None = None,
) -> list[str]:
    """Split text recursively using a hierarchy of separators."""
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    chunks = []
    current_sep = separators[0]
    remaining_seps = separators[1:] if len(separators) > 1 else [""]

    parts = text.split(current_sep) if current_sep else list(text)

    current_chunk = ""
    for part in parts:
        test_chunk = current_chunk + current_sep + part if current_chunk else part
        if len(test_chunk) <= chunk_size:
            current_chunk = test_chunk
        else:
            if current_chunk:
                if len(current_chunk) > chunk_size and remaining_seps:
                    chunks.extend(recursive_character_split(
                        current_chunk, chunk_size, chunk_overlap, remaining_seps
                    ))
                else:
                    chunks.append(current_chunk.strip())
            current_chunk = part

    if current_chunk and current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Apply overlap
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_end = chunks[i - 1][-chunk_overlap:]
            overlapped.append(prev_end + " " + chunks[i])
        return overlapped

    return chunks


def section_aware_split(text: str, chunk_size: int = 512) -> list[str]:
    """Split text by sections (headers) preserving section context."""
    section_pattern = r'^(?:#{1,3}\s+.+|[A-Z][A-Z\s&]{2,}(?:\n|$))'
    lines = text.split("\n")
    sections = []
    current_section = ""
    current_header = ""

    for line in lines:
        if re.match(section_pattern, line.strip()):
            if current_section.strip():
                sections.append(current_section.strip())
            current_header = line.strip()
            current_section = current_header + "\n"
        else:
            current_section += line + "\n"

    if current_section.strip():
        sections.append(current_section.strip())

    # Sub-split sections that are too large
    final_chunks = []
    for section in sections:
        if len(section) <= chunk_size:
            final_chunks.append(section)
        else:
            sub_chunks = recursive_character_split(section, chunk_size)
            final_chunks.extend(sub_chunks)

    return final_chunks


def chunk_resume(
    raw_text: str,
    resume_id: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[Chunk]:
    """Chunk a resume using section-aware splitting."""
    text_chunks = section_aware_split(raw_text, chunk_size)
    return [
        Chunk(
            text=text,
            index=i,
            source_id=resume_id,
            source_type="resume",
            metadata={"chunk_total": len(text_chunks)},
        )
        for i, text in enumerate(text_chunks)
        if text.strip()
    ]


def chunk_knowledge_doc(
    text: str,
    doc_id: str,
    doc_type: str = "knowledge_base",
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[Chunk]:
    """Chunk a knowledge base document."""
    text_chunks = recursive_character_split(text, chunk_size, chunk_overlap)
    return [
        Chunk(
            text=t,
            index=i,
            source_id=doc_id,
            source_type=doc_type,
            metadata={"chunk_total": len(text_chunks)},
        )
        for i, t in enumerate(text_chunks)
        if t.strip()
    ]
