"""Unit tests for the live-data API agent."""

from __future__ import annotations

from agentic.agents.api_agent import APIAgent, MockPropertyAPIClient
from agentic.agents.api_models import APIIntent, APIRequest, APIResponse, APIResponsePayload
from agentic.workflow.state import AgentState


def _build_agent() -> APIAgent:
    """Helper that always uses the deterministic mock client."""
    return APIAgent(client=MockPropertyAPIClient(), use_live_client=False)


def test_build_request_extracts_branch_type_and_memory_shortname():
    agent = _build_agent()
    state = AgentState(
        query="Show available garage units in Bandel",
        memory={"facts": {"last_project": "SHIVALAYA"}},
    )

    request = agent._build_request(state)

    assert request.intent == APIIntent.AVAILABILITY_BY_CITY
    assert request.shortname == "SHIVALAYA"
    assert request.branch == "BANDEL"
    assert request.property_type == "Garage"


def test_api_agent_populates_state_with_summary_and_metadata():
    agent = _build_agent()
    state = AgentState(
        query="Any flats available right now?",
        memory={"facts": {"last_project": "SHIVALAYA"}},
    )

    updated = agent(state)

    assert updated.api_response is not None
    assert updated.api_response.answer.startswith("SHIVALAYA currently has")
    assert updated.api_response.metadata["agent"] == "api_agent"
    assert updated.api_response.metadata["intent"] == "AVAILABILITY_BY_PROJECT"
    assert updated.api_response.metadata["total_units"] == 20
    assert updated.api_response.metadata["available_units"] == 5
    assert updated.memory["facts"]["last_project"] == "SHIVALAYA"


def test_format_answer_handles_downstream_error():
    agent = _build_agent()
    payload = APIResponsePayload(status="error", data={}, endpoint="/project/search")
    response = APIResponse(intent=APIIntent.PROJECT_METADATA, payload=payload)
    request = APIRequest(intent=APIIntent.PROJECT_METADATA, user_query="status?", shortname="SHIVALAYA")

    answer, metadata = agent._format_answer(response, request)

    assert "couldn't retrieve" in answer.lower()
    assert metadata["status"] == "error"
    assert metadata["endpoint"] == "/project/search"
