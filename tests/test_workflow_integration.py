"""Integration tests covering routing and LangGraph workflow behavior."""

from __future__ import annotations

from typing import Any, Dict

from agentic.workflow.orchestrator import create_initial_state
from agentic.workflow.routing import HeuristicRouter

from .conftest import GROUND_TRUTH_RAG_ANSWER


def _get_answer(result: Dict[str, Any]) -> str:
    response = result.get("final_response")
    assert response is not None, "final_response missing from workflow output"
    return response.answer or ""


def _get_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    response = result.get("final_response")
    assert response is not None, "final_response missing from workflow output"
    return response.metadata or {}


router = HeuristicRouter()


def test_router_prefers_rag_keywords():
    decision = router.route("Tell me about Astha amenities and history")
    assert decision.target == "rag"
    assert "RAG_CONTEXT" in decision.intents
    assert decision.confidence > 0.65


def test_router_detects_api_intent():
    decision = router.route("How many flats are available in Shivalaya right now?")
    assert decision.target == "api"
    assert decision.intents == ["AVAILABILITY_BY_PROJECT"]
    assert decision.confidence > 0.7


def test_router_detects_hybrid_queries():
    decision = router.route("Tell me about Astha and show current available flats in Bandel")
    assert decision.target == "both"
    assert "RAG_CONTEXT" in decision.intents
    assert any(intent.startswith("AVAILABILITY") for intent in decision.intents)


def test_workflow_returns_rag_answer_when_routed(workflow_graph, workflow_config):
    state = create_initial_state("Tell me about Astha's service areas")
    result = workflow_graph.invoke(state, config=workflow_config)

    assert result["routing"]["target"] == "rag"
    assert result["api_response"] is None
    answer = _get_answer(result)
    assert GROUND_TRUTH_RAG_ANSWER in answer
    metadata = _get_metadata(result)
    assert metadata.get("agent") == "rag_agent"


def test_workflow_returns_api_answer_when_routed(workflow_graph, workflow_config):
    memory = {"facts": {"last_project": "SHIVALAYA"}}
    state = create_initial_state("How many flats are available in Shivalaya right now?", memory=memory)
    result = workflow_graph.invoke(state, config=workflow_config)

    assert result["routing"]["target"] == "api"
    assert result["rag_response"] is None
    answer = _get_answer(result)
    assert "SHIVALAYA currently has 5 Flats available" in answer
    metadata = _get_metadata(result)
    assert metadata.get("agent") == "api_agent"


def test_workflow_combines_answers_for_hybrid_queries(workflow_graph, workflow_config):
    state = create_initial_state("Tell me about Astha and show current available flats in Bandel")
    result = workflow_graph.invoke(state, config=workflow_config)

    assert result["routing"]["target"] == "both"
    answer = _get_answer(result)
    assert GROUND_TRUTH_RAG_ANSWER in answer
    assert "Bandel" in answer
    metadata = _get_metadata(result)
    assert metadata.get("agent") == "aggregator"
    components = metadata.get("components", [])
    assert len(components) == 2