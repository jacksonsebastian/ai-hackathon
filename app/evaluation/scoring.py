"""
Answer scoring and evaluation engine.
"""

from typing import Dict, Any

class ScoringEngine:
    """Handles logic for calculating composite scores from individual evaluations."""
    
    @staticmethod
    def calculate_composite(scores: Dict[str, float]) -> float:
        """Calculate weighted composite score."""
        if not scores:
            return 0.0
        
        # Simplified equal weighting for hackathon
        total = sum(scores.values())
        return round(total / len(scores), 2)
        
    @staticmethod
    def get_hiring_recommendation(overall_score: float) -> str:
        if overall_score >= 80:
            return "strong_hire"
        elif overall_score >= 65:
            return "hire"
        elif overall_score >= 50:
            return "maybe"
        return "no_hire"
