"""Conversation memory primitives for the agentic workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MemoryMessage:
    """Represents a single message in the conversation history."""

    role: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationMemory:
    """Simple in-memory store for conversation history and extracted facts."""

    messages: List[MemoryMessage] = field(default_factory=list)
    facts: Dict[str, Any] = field(default_factory=dict)

    def append(self, role: str, content: str, **metadata: Any) -> None:
        """Append a message to the conversation history."""
        self.messages.append(MemoryMessage(role=role, content=content, metadata=metadata))

    def get_history(self, limit: int | None = None) -> List[MemoryMessage]:
        """Return the most recent messages up to ``limit``."""
        if limit is None or limit >= len(self.messages):
            return list(self.messages)
        return self.messages[-limit:]

    def update_fact(self, key: str, value: Any) -> None:
        """Store or update a derived fact."""
        self.facts[key] = value

    def export_state(self) -> Dict[str, Any]:
        """Serialize memory for LangGraph state propagation."""
        return {
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                    "metadata": message.metadata,
                }
                for message in self.messages
            ],
            "facts": dict(self.facts),
        }
