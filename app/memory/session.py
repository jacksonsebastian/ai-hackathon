"""
Interview session state management.
"""
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class SessionState:
    session_id: str
    current_round: str = "init"
    candidate_profile: str = ""
    scores: Dict[str, float] = field(default_factory=dict)
    
    def update_score(self, category: str, score: float):
        self.scores[category] = score
