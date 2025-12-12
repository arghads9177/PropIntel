"""RAG agent node built on top of the existing retrieval pipeline."""

from __future__ import annotations

from typing import Any, Dict

from agentic.agents.base import AgentConfig, AgentNode, _prepare_agent_response
from agentic.workflow.state import AgentState
from retrieval.retrieval_orchestrator import RetrievalOrchestrator


class RAGAgent(AgentNode):
    """Wraps the RetrievalOrchestrator for use inside LangGraph."""

    def __init__(self, *, orchestrator: RetrievalOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or RetrievalOrchestrator()
        self.config = AgentConfig(
            name="rag_agent",
            description="Answers questions using the PropIntel RAG pipeline",
        )

    def __call__(self, state: AgentState, **kwargs: Any) -> AgentState:
        if not state.query:
            state.rag_response = _prepare_agent_response(
                "I did not receive a query to search.",
                metadata={"agent": self.config.name, "error": "empty_query"},
            )
            return state

        retrieval_response = self.orchestrator.retrieve(
            query=state.query,
            n_results=kwargs.get("n_results", 5),
            use_query_expansion=kwargs.get("use_query_expansion", True),
            ranking_strategy=kwargs.get("ranking_strategy", "hybrid"),
        )

        answer = retrieval_response.get("summary") or retrieval_response.get("answer")
        if not answer:
            answer = "I could not find enough information in the knowledge base."

        state.rag_response = _prepare_agent_response(
            answer,
            sources=self._extract_sources(retrieval_response),
            metadata={
                "agent": self.config.name,
                "query_type": retrieval_response.get("metadata", {}).get("query_type"),
                "collection": retrieval_response.get("metadata", {}).get("collection"),
            },
        )
        return state

    @staticmethod
    def _extract_sources(response: Dict[str, Any]) -> list[Dict[str, Any]]:
        results = response.get("results", [])
        sources = []
        for result in results:
            metadata = result.get("metadata", {})
            sources.append(
                {
                    "chunk_id": metadata.get("chunk_id"),
                    "project_name": metadata.get("project_name") or metadata.get("company_id"),
                    "section": metadata.get("section") or metadata.get("chunk_type"),
                    "score": result.get("score"),
                }
            )
        return sources


def build_rag_agent(**kwargs: Any) -> RAGAgent:
    """Factory for dependency injection."""
    return RAGAgent(**kwargs)
