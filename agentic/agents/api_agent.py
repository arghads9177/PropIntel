"""Stub implementation of the API agent node."""

from __future__ import annotations

from typing import Any

from agentic.agents.base import AgentConfig, AgentNode, _prepare_agent_response
from agentic.workflow.state import AgentState


class APIAgent(AgentNode):
    """Temporary stub that simulates external API lookups."""

    def __init__(self) -> None:
        self.config = AgentConfig(
            name="api_agent",
            description="Fetches live booking or pricing data via external APIs",
        )

    def __call__(self, state: AgentState, **kwargs: Any) -> AgentState:
        # TODO: Replace with real API integration when endpoints are available.
        requested_field = kwargs.get("field", "booking_status")
        answer = (
            "(Stub) I would normally call the booking/pricing API here to retrieve "
            f"the latest {requested_field} information."
        )
        state.api_response = _prepare_agent_response(
            answer,
            metadata={"agent": self.config.name, "stub": True, "requested_field": requested_field},
        )
        return state


def build_api_agent() -> APIAgent:
    return APIAgent()
