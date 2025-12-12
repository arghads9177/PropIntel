"""LangGraph state definitions for the PropIntel agentic workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AgentResponse:
    """Standardized response payload returned by individual agents."""

    answer: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    sources: list[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentState:
    """Shared graph state propagated across LangGraph nodes."""

    query: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)
    routing: Dict[str, Any] = field(default_factory=dict)
    rag_response: AgentResponse | None = None
    api_response: AgentResponse | None = None
    final_response: AgentResponse | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the state into plain dictionaries for LangGraph."""
        return {
            "query": self.query,
            "context": self.context,
            "memory": self.memory,
            "routing": self.routing,
            "rag_response": self._response_to_dict(self.rag_response),
            "api_response": self._response_to_dict(self.api_response),
            "final_response": self._response_to_dict(self.final_response),
        }

    @staticmethod
    def _response_to_dict(response: AgentResponse | None) -> Optional[Dict[str, Any]]:
        if response is None:
            return None
        return {
            "answer": response.answer,
            "metadata": response.metadata,
            "sources": response.sources,
        }


def create_initial_state(query: str, memory: Dict[str, Any] | None = None) -> AgentState:
    """Helper to bootstrap the state from the CLI input."""
    return AgentState(query=query, memory=memory or {})
