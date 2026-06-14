"""
Evaluation rubrics and feedback formatting.
"""

from typing import Dict, Any

def format_rubric_feedback(scores: Dict[str, float], reasoning: str) -> str:
    """Format scoring output into readable feedback."""
    feedback = "### Evaluation Scores\n\n"
    for dim, score in scores.items():
        feedback += f"- **{dim.replace('_', ' ').title()}**: {score}/10\n"
    feedback += f"\n**Reasoning:**\n{reasoning}"
    return feedback

