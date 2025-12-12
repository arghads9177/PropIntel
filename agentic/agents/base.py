"""Shared utilities for agent nodes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from agentic.workflow.state import AgentResponse, AgentState


@dataclass
class AgentConfig:
    """Generic configuration shared by agents."""

    name: str
    description: str


class AgentNode(Protocol):
    """Protocol for LangGraph-compatible agent callables."""

    config: AgentConfig

    def __call__(self, state: AgentState, **kwargs: Any) -> AgentState:  # pragma: no cover - interface only
        ...


def _prepare_agent_response(answer: str, *, sources: list[Dict[str, Any]] | None = None, metadata: Dict[str, Any] | None = None) -> AgentResponse:
    """Helper to standardize responses."""
    return AgentResponse(
        answer=answer,
        sources=sources or [],
        metadata=metadata or {},
    )
