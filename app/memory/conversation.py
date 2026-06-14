"""
Conversation memory management.
"""
from typing import List, Dict

class ConversationMemory:
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-(self.max_history * 2):]

    def get_context(self) -> str:
        return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.history])

    def clear(self):
        self.history = []
