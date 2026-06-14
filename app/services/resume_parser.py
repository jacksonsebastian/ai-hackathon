"""
Resume parsing service.

Handles PDF/DOCX upload, text extraction, and LLM-powered
structured data extraction into candidate profiles.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from app.database.models import Resume
from app.database import crud
from app.prompts.templates import build_resume_parse_prompt
from app.services.ai_service import AIService
from app.utils.helpers import generate_id, now_utc, hash_content, extract_json_from_response
from app.utils.logger import get_service_logger

logger = get_service_logger("resume_parser")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("PyMuPDF not installed. Install with: pip install pymupdf")
        return "[PDF extraction requires PyMuPDF. Install with: pip install pymupdf]"
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return f"[Error extracting PDF: {e}]"


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    text_parts.append(row_text)
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("python-docx not installed. Install with: pip install python-docx")
        return "[DOCX extraction requires python-docx. Install with: pip install python-docx]"
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        return f"[Error extracting DOCX: {e}]"


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from a resume file based on extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use PDF or DOCX.")


async def parse_resume(
    file_bytes: bytes,
    filename: str,
    ai_service: Optional[AIService] = None,
) -> Resume:
    """
    Full resume parsing pipeline:
    1. Extract raw text from PDF/DOCX
    2. Use LLM to extract structured data
    3. Store in database
    4. Return Resume model
    """
    logger.info(f"Parsing resume: {filename}")

    # Step 1: Extract raw text
    raw_text = extract_text(file_bytes, filename)
    if not raw_text or raw_text.startswith("["):
        logger.warning(f"Limited text extraction for {filename}")

    # Step 2: Check for duplicates
    content_hash = hash_content(raw_text)
    
    # Step 3: LLM-powered structured extraction
    service = ai_service or AIService()
    prompt = build_resume_parse_prompt(raw_text)
    
    result = await service.generate_structured(
        prompt=prompt,
        system_prompt="You are an expert resume parser. Extract structured data accurately.",
    )

    # Step 4: Build Resume model
    ext = Path(filename).suffix.lower().lstrip(".")
    resume = Resume(
        id=generate_id(),
        filename=filename,
        file_type=ext,
        raw_text=raw_text,
        candidate_name=result.get("candidate_name", "Unknown"),
        email=result.get("email", ""),
        phone=result.get("phone", ""),
        skills=result.get("skills", []),
        experience=result.get("experience", []),
        education=result.get("education", []),
        projects=result.get("projects", []),
        certifications=result.get("certifications", []),
        technologies=result.get("technologies", []),
        summary=result.get("summary", ""),
        strengths=result.get("strengths", []),
        gaps=result.get("gaps", []),
        content_hash=content_hash,
        created_at=now_utc(),
        updated_at=now_utc(),
    )

    # Step 5: Store in database
    crud.create_resume(resume)
    logger.info(f"Resume parsed and stored: {resume.candidate_name} (id={resume.id})")

    return resume


def parse_resume_basic(file_bytes: bytes, filename: str) -> Resume:
    """
    Basic synchronous resume parsing without LLM.
    Extracts text only, useful for quick uploads.
    """
    raw_text = extract_text(file_bytes, filename)
    ext = Path(filename).suffix.lower().lstrip(".")
    
    resume = Resume(
        id=generate_id(),
        filename=filename,
        file_type=ext,
        raw_text=raw_text,
        candidate_name="Pending Analysis",
        content_hash=hash_content(raw_text),
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    
    crud.create_resume(resume)
    return resume
