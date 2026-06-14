"""
Input validation utilities.
"""
from typing import Any, Dict
import os

def validate_resume_file(file_name: str, file_size: int) -> bool:
    """Validate resume file extension and size."""
    allowed_extensions = ['.pdf', '.docx']
    max_size = 10 * 1024 * 1024 # 10MB
    ext = os.path.splitext(file_name)[1].lower()
    return ext in allowed_extensions and file_size <= max_size

def validate_interview_config(config: Dict[str, Any]) -> bool:
    """Validate interview configuration payload."""
    required_keys = ['candidate_name', 'interview_type', 'difficulty']
    return all(key in config for key in required_keys)
