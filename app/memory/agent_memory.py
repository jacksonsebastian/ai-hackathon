"""
Shared agent memory for cross-agent collaboration.
"""
from typing import Dict, Any

class AgentMemory:
    def __init__(self):
        self.shared_state: Dict[str, Any] = {}

    def set(self, key: str, value: Any):
        self.shared_state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.shared_state.get(key, default)

    def update(self, data: Dict[str, Any]):
        self.shared_state.update(data)
