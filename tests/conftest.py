"""Shared test fixtures and doubles for workflow integration tests."""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict

import pytest

from agentic.agents.api_agent import APIAgent, MockPropertyAPIClient
from agentic.agents.base import AgentConfig, _prepare_agent_response
from agentic.workflow.orchestrator import build_agentic_graph, create_initial_state
from agentic.workflow.state import AgentState

GROUND_TRUTH_RAG_ANSWER = (
    "Astha Infra Realty operates across Asansol, Bandel, and Hooghly with a focus on"
    " residential and commercial developments."
)
GROUND_TRUTH_SOURCE = {
    "chunk_id": "chunk-service-areas",
    "project_name": "Astha Infra Realty Ltd.",
    "section": "service_areas",
}


class StubRAGAgent:
    """Deterministic RAG agent substitute for tests."""

    def __init__(self, answer: str = GROUND_TRUTH_RAG_ANSWER) -> None:
        self.answer = answer
        self.config = AgentConfig(name="rag_agent", description="Stub RAG agent")

    def __call__(self, state: AgentState, **_: Any) -> AgentState:
        state.rag_response = _prepare_agent_response(
            self.answer,
            sources=[GROUND_TRUTH_SOURCE],
            metadata={
                "agent": self.config.name,
                "source": "stub_rag",
                "ground_truth": True,
            },
        )

        memory = state.memory or {}
        facts = memory.setdefault("facts", {})
        facts.setdefault("last_project", "SHIVALAYA")

        history = memory.setdefault("history", [])
        history.extend(
            [
                {"role": "user", "content": state.query},
                {"role": "assistant", "content": self.answer},
            ]
        )
        memory["history"] = history[-8:]
        state.memory = memory
        return state


@pytest.fixture
def stub_rag_agent() -> StubRAGAgent:
    return StubRAGAgent()


@pytest.fixture
def mock_api_agent() -> APIAgent:
    return APIAgent(client=MockPropertyAPIClient(), use_live_client=False)


@pytest.fixture
def workflow_graph(stub_rag_agent: StubRAGAgent, mock_api_agent: APIAgent):
    return build_agentic_graph(rag_agent=stub_rag_agent, api_agent=mock_api_agent)


@pytest.fixture
def workflow_config() -> Dict[str, Dict[str, str]]:
    return {"configurable": {"thread_id": f"test-thread-{uuid.uuid4()}"}}


@pytest.fixture
def run_workflow(workflow_graph, workflow_config) -> Callable[[str, Dict[str, Any] | None], Dict[str, Any]]:
    def _run(query: str, memory: Dict[str, Any] | None = None) -> Dict[str, Any]:
        state = create_initial_state(query=query, memory=memory or {})
        return workflow_graph.invoke(state, config=workflow_config)

    return _run
