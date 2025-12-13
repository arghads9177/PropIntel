"""Stub implementation of the API agent node."""

from __future__ import annotations

import random
import time
from typing import Any, Dict, Optional, Protocol

from agentic.agents.api_models import APIIntent, APIRequest, APIResponse, APIResponsePayload
from agentic.agents.base import AgentConfig, AgentNode, _prepare_agent_response
from agentic.workflow.state import AgentState


class PropertyAPIClient(Protocol):
    """Protocol implemented by real or stub API clients."""

    def fetch(self, request: APIRequest) -> APIResponse:  # pragma: no cover - interface only
        ...


class MockPropertyAPIClient:
    """In-memory stub with deterministic pseudo-random outputs."""

    SAMPLE_DATA: Dict[str, Dict[str, Any]] = {
        "shivalaya": {
            "booking_status": "75% of units booked",
            "average_price": "₹4,850 per sq.ft",
            "available_units": 22,
        },
        "kabi tirtha": {
            "booking_status": "Running, phases 1-3 sold",
            "average_price": "₹5,200 per sq.ft",
            "available_units": 10,
        },
    }

    def fetch(self, request: APIRequest) -> APIResponse:
        key = (request.property_name or "unknown").lower()
        payload = self.SAMPLE_DATA.get(key, {
            "booking_status": "Data not available in stub",
            "average_price": "N/A",
            "available_units": 0,
        })

        # Simulate latency for traceability
        start = time.perf_counter()
        time.sleep(0.05)
        latency_ms = int((time.perf_counter() - start) * 1000)

        field_map = {
            APIIntent.BOOKING_STATUS: "booking_status",
            APIIntent.PRICE_LOOKUP: "average_price",
            APIIntent.INVENTORY: "available_units",
        }
        field = field_map.get(request.intent, "booking_status")
        value = payload.get(field)

        return APIResponse(
            intent=request.intent,
            payload=APIResponsePayload(
                status="ok",
                data={
                    "property": request.property_name,
                    "tower": request.tower_id,
                    "field": field,
                    "value": value,
                },
            ),
            metadata={
                "stub": True,
                "trace_id": f"stub-{random.randint(1000, 9999)}",
                "latency_ms": latency_ms,
            },
        )


class APIAgent(AgentNode):
    """LangGraph node that delegates to a property API client."""

    def __init__(self, client: PropertyAPIClient | None = None) -> None:
        self.client = client or MockPropertyAPIClient()
        self.config = AgentConfig(
            name="api_agent",
            description="Fetches live booking or pricing data via external APIs",
        )

    def __call__(self, state: AgentState, **kwargs: Any) -> AgentState:
        request = self._build_request(state, **kwargs)
        response = self.client.fetch(request)

        state.api_response = _prepare_agent_response(
            self._format_answer(response),
            metadata={
                "agent": self.config.name,
                "intent": response.intent.name,
                **response.metadata,
            },
        )
        return state

    def _build_request(self, state: AgentState, **overrides: Any) -> APIRequest:
        query = state.query or overrides.get("query", "")
        intent = overrides.get("intent") or self._infer_intent(query)
        property_name = overrides.get("property_name") or self._extract_property(state)
        tower_id = overrides.get("tower_id")
        return APIRequest(
            intent=intent,
            property_name=property_name,
            tower_id=tower_id,
            user_query=query,
            extra_params={k: v for k, v in overrides.items() if k not in {"intent", "property_name", "tower_id"}},
        )

    @staticmethod
    def _infer_intent(query: str) -> APIIntent:
        lower = query.lower()
        if any(term in lower for term in ("price", "cost", "rate")):
            return APIIntent.PRICE_LOOKUP
        if any(term in lower for term in ("book", "booking", "sold")):
            return APIIntent.BOOKING_STATUS
        if any(term in lower for term in ("available", "inventory", "units")):
            return APIIntent.INVENTORY
        return APIIntent.UNKNOWN

    @staticmethod
    def _extract_property(state: AgentState) -> Optional[str]:
        facts = (state.memory or {}).get("facts", {})
        return facts.get("last_project")

    @staticmethod
    def _format_answer(response: APIResponse) -> str:
        field = response.payload.data.get("field")
        value = response.payload.data.get("value")
        property_name = response.payload.data.get("property") or "the property"
        if value in (None, "N/A"):
            return f"Live {field} data for {property_name} is not available in the stub."
        return f"According to the latest API data, the {field} for {property_name} is {value}."


def build_api_agent(client: PropertyAPIClient | None = None) -> APIAgent:
    return APIAgent(client=client)
