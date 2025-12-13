"""Unit tests for the agentic RAG node."""

from __future__ import annotations

import pytest

from agentic.agents.rag_agent import RAGAgent
from agentic.workflow.state import AgentState, AgentResponse, create_initial_state


class StubAnswerGenerator:
    """Deterministic AnswerGenerator stand-in for tests."""

    def __init__(self, answer_text: str = "Stub answer", score: float = 0.91) -> None:
        self.answer_text = answer_text
        self.score = score
        self.calls: list[dict] = []

    def generate_answer(self, **kwargs):  # type: ignore[override]
        self.calls.append(kwargs)
        query = kwargs.get("query", "")
        metadata = {
            "query_type": "location",
            "retrieval_strategy": kwargs.get("ranking_strategy", "hybrid"),
        }
        result_metadata = {
            "project_name": "Shivalaya",
            "chunk_id": "chunk-1",
            "section": "location",
        }
        return {
            "query": query,
            "answer": f"{self.answer_text}: {query}",
            "sources": [
                {
                    "chunk_id": "chunk-1",
                    "project_name": "Shivalaya",
                    "section": "location",
                    "score": self.score,
                }
            ],
            "metadata": metadata,
            "retrieval_results": [
                {
                    "metadata": result_metadata,
                    "score": self.score,
                }
            ],
        }


def test_rag_agent_returns_structured_response():
    stub = StubAnswerGenerator()
    agent = RAGAgent(answer_generator=stub)
    state = create_initial_state("Where is Shivalaya?", memory={"history": []})

    updated = agent(state)

    assert updated.rag_response is not None
    assert updated.rag_response.answer.startswith("Stub answer")
    assert updated.rag_response.metadata["agent"] == "rag_agent"
    assert pytest.approx(updated.rag_response.metadata["confidence"], 0.01) == 0.91
    assert updated.context["enriched_query"] == "Where is Shivalaya?"
    assert updated.memory["history"][-1]["role"] == "assistant"


def test_rag_agent_enriches_followup_with_memory():
    stub = StubAnswerGenerator()
    agent = RAGAgent(answer_generator=stub)
    memory = {"facts": {"last_project": "Shivalaya"}, "history": []}
    state = create_initial_state("How tall is it?", memory=memory)

    updated = agent(state)

    enriched_query = updated.context["enriched_query"]
    assert "Shivalaya" in enriched_query
    assert stub.calls[-1]["query"] == enriched_query


def test_rag_agent_handles_empty_query():
    agent = RAGAgent(answer_generator=StubAnswerGenerator())
    state = AgentState(query="")

    updated = agent(state)

    assert isinstance(updated.rag_response, AgentResponse)
    assert updated.rag_response.metadata.get("error") == "empty_query"