"""
Resume parsing service — AI-First.

Flow: Resume File → PDF/DOCX Extraction → Clean Text → DeepSeek-R1 → JSON → Validation → Database

ALL resume understanding is done by DeepSeek-R1.
No regex extraction. No hardcoded skills. No heuristics. No fabrication.
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Optional

from app.database.models import Resume
from app.database import crud
from app.services.ai_service import AIService
from app.utils.helpers import generate_id, now_utc, hash_content, extract_json_from_response
from app.utils.logger import get_service_logger

logger = get_service_logger("resume_parser")

# ── Resume Extraction Prompt ─────────────────────────────────

RESUME_EXTRACTION_PROMPT = """You are an expert resume parser. Your job is to extract structured data from the resume text below.

STRICT RULES:
- Extract ONLY information explicitly present in the resume.
- NEVER hallucinate, guess, infer, or fabricate any data.
- If a field is not found in the resume, return null for that field.
- Skills must come ONLY from the resume content, not from your training data.
- Do NOT invent certifications, projects, or contact information.
- Return ONLY valid JSON. No markdown, no code blocks, no explanations.

RESUME TEXT:
---
{resume_text}
---

Return this exact JSON structure:
{{
    "candidate_name": "<full name or null if not found>",
    "email": "<email or null if not found>",
    "phone": "<phone or null if not found>",
    "location": "<location or null if not found>",
    "linkedin": "<linkedin URL or null if not found>",
    "github": "<github URL or null if not found>",
    "summary": "<2-3 sentence professional summary based on resume content>",
    "skills": ["<only skills explicitly mentioned in resume>"],
    "technologies": ["<only technologies/tools explicitly mentioned>"],
    "experience": [
        {{
            "title": "<job title>",
            "company": "<company name>",
            "duration": "<time period>",
            "description": "<key responsibilities and achievements>"
        }}
    ],
    "education": [
        {{
            "degree": "<degree>",
            "institution": "<university/college>",
            "year": "<graduation year or period>"
        }}
    ],
    "projects": [
        {{
            "name": "<project name>",
            "description": "<what the project does>",
            "technologies": ["<tech used>"]
        }}
    ],
    "certifications": ["<only certifications explicitly listed>"],
    "strengths": ["<strengths based on resume evidence>"],
    "gaps": ["<areas where resume shows limited experience>"]
}}"""


# ── Text Extraction ──────────────────────────────────────────

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
        raise RuntimeError("PyMuPDF not installed. Install with: pip install pymupdf")
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {e}")


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
        raise RuntimeError("python-docx not installed. Install with: pip install python-docx")
    except Exception as e:
        raise RuntimeError(f"DOCX extraction failed: {e}")


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from a resume file based on extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use PDF or DOCX.")


def clean_text(raw_text: str) -> str:
    """Clean extracted text: normalize whitespace, remove artifacts."""
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', raw_text)
    # Remove null bytes and control chars (except newline/tab)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.strip()


# ── AI Resume Parser ─────────────────────────────────────────

async def parse_resume(
    file_bytes: bytes,
    filename: str,
    ai_service: Optional[AIService] = None,
) -> Resume:
    """
    AI-first resume parsing pipeline.

    Flow: File → Extract Text → Clean → DeepSeek-R1 → JSON → Validate → DB

    All resume understanding is done by DeepSeek-R1.
    No regex. No hardcoded skills. No heuristics.
    """
    logger.info(f"Parsing resume: {filename}")

    # ── Step 1: Extract raw text ──
    raw_text = extract_text(file_bytes, filename)
    cleaned = clean_text(raw_text)
    logger.info(f"Extracted {len(cleaned)} characters from {filename}")

    if len(cleaned) < 50:
        raise ValueError(f"Resume text too short ({len(cleaned)} chars). Check file content.")

    content_hash = hash_content(cleaned)

    # ── Step 2: LLM extraction with retry ──
    service = ai_service or AIService()
    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=cleaned[:6000])

    result = None
    last_error = None

    for attempt in range(3):
        try:
            llm_result = await service.generate_structured(
                prompt=prompt,
                system_prompt="You are a resume parser. Return ONLY valid JSON. No text before or after the JSON.",
            )
            
            # Validate we got actual parsed data (not just raw_response)
            if "raw_response" not in llm_result and llm_result.get("candidate_name"):
                result = llm_result
                logger.info(f"LLM extraction succeeded on attempt {attempt + 1}")
                break
            elif "raw_response" in llm_result:
                # Try to extract JSON from raw response
                parsed = extract_json_from_response(llm_result["raw_response"])
                if parsed and parsed.get("candidate_name"):
                    result = parsed
                    logger.info(f"LLM extraction succeeded (from raw) on attempt {attempt + 1}")
                    break
                else:
                    last_error = "LLM returned text but JSON extraction failed"
                    logger.warning(f"Attempt {attempt + 1}: {last_error}")
            else:
                last_error = "LLM returned JSON but candidate_name is missing"
                logger.warning(f"Attempt {attempt + 1}: {last_error}")
                # Use what we got even without name
                result = llm_result
                break

        except Exception as e:
            last_error = str(e)
            logger.warning(f"LLM attempt {attempt + 1} failed: {e}")

    if result is None:
        raise RuntimeError(
            f"Resume parsing failed after 3 attempts. Last error: {last_error}. "
            f"The AI model could not extract structured data from this resume."
        )

    # ── Step 3: Build Resume model ──
    def safe_get(key, default=None):
        """Get value from result, treating null/'Not Found' as missing."""
        val = result.get(key, default)
        if val is None or val == "Not Found" or val == "null":
            return default
        return val

    ext = Path(filename).suffix.lower().lstrip(".")
    resume = Resume(
        id=generate_id(),
        filename=filename,
        file_type=ext,
        raw_text=raw_text,
        candidate_name=safe_get("candidate_name", "Not Found"),
        email=safe_get("email", ""),
        phone=safe_get("phone", ""),
        skills=safe_get("skills", []),
        experience=safe_get("experience", []),
        education=safe_get("education", []),
        projects=safe_get("projects", []),
        certifications=safe_get("certifications", []),
        technologies=safe_get("technologies", []),
        summary=safe_get("summary", ""),
        strengths=safe_get("strengths", []),
        gaps=safe_get("gaps", []),
        content_hash=content_hash,
        created_at=now_utc(),
        updated_at=now_utc(),
    )

    # ── Step 4: Store in database ──
    saved_resume = crud.create_resume(resume)
    logger.info(f"Resume parsed by AI: {saved_resume.candidate_name} (id={saved_resume.id})")

    return saved_resume
