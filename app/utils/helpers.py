"""
Utility helpers for the AI Interviewer Agent System.

Common functions for text processing, token estimation,
file handling, and data transformations.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def generate_id() -> str:
    """Generate a unique ID for database records."""
    return str(uuid.uuid4())


def now_utc() -> str:
    """Get current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def now_local() -> str:
    """Get current local timestamp as ISO string."""
    return datetime.now().isoformat()


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a text string.
    Uses a rough heuristic of ~4 chars per token.
    """
    return max(1, len(text) // 4)


def truncate_text(text: str, max_tokens: int = 2000) -> str:
    """Truncate text to approximately max_tokens."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "... [truncated]"


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove non-printable characters
    text = re.sub(r'[^\x20-\x7E\n\t]', '', text)
    return text.strip()


def extract_json_from_response(text: str) -> Optional[dict]:
    """
    Extract JSON from an LLM response that may contain
    markdown code blocks or other formatting.
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try extracting from markdown code block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # Try finding JSON object in text
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None


def hash_content(content: str) -> str:
    """Generate SHA-256 hash of content for deduplication."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h {mins}m"


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """Safely serialize object to JSON, handling non-serializable types."""
    def default_handler(o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Path):
            return str(o)
        if hasattr(o, '__dict__'):
            return o.__dict__
        return str(o)
    
    return json.dumps(obj, indent=indent, default=default_handler, ensure_ascii=False)


def chunk_list(lst: list, chunk_size: int) -> list[list]:
    """Split a list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')[:200]


def parse_skills_list(text: str) -> list[str]:
    """Parse a comma/newline separated skills string into a clean list."""
    # Split on commas, newlines, semicolons, or pipes
    skills = re.split(r'[,;\n|•·]', text)
    # Clean each skill
    skills = [s.strip().strip('-').strip() for s in skills]
    # Remove empty strings and duplicates while preserving order
    seen = set()
    result = []
    for skill in skills:
        lower = skill.lower()
        if skill and lower not in seen:
            seen.add(lower)
            result.append(skill)
    return result
