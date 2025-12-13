"""RAG agent node built on top of the existing retrieval/prompt pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agentic.agents.base import AgentConfig, AgentNode, _prepare_agent_response
from agentic.workflow.state import AgentResponse, AgentState
from generation.answer_generator import AnswerGenerator


FOLLOW_UP_TOKENS = ("it", "them", "they", "there", "that", "those", "same", "him", "her")


class RAGAgent(AgentNode):
    """Wraps the AnswerGenerator for use inside LangGraph."""

    def __init__(self, *, answer_generator: AnswerGenerator | None = None) -> None:
        self.answer_generator = answer_generator or AnswerGenerator()
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

        self._maybe_switch_collection(state)
        enriched_query = self._enrich_query_with_memory(state)
        template_name = kwargs.get("template_name", state.context.get("template", "default"))

        answer_payload = self.answer_generator.generate_answer(
            query=enriched_query,
            n_results=kwargs.get("n_results", 5),
            template_name=template_name,
            ranking_strategy=kwargs.get("ranking_strategy", "hybrid"),
            use_query_expansion=kwargs.get("use_query_expansion", True),
            include_sources=True,
        )

        state.context["enriched_query"] = enriched_query
        state.context["last_query_type"] = answer_payload.get("metadata", {}).get("query_type")

        state.rag_response = _prepare_agent_response(
            answer_payload.get("answer") or "I could not find enough information in the knowledge base.",
            sources=answer_payload.get("sources") or self._extract_sources(answer_payload),
            metadata=self._build_metadata(answer_payload, state),
        )

        self._update_memory(state, answer_payload)
        return state

    # -----------------
    # Helper functions
    # -----------------

    def _enrich_query_with_memory(self, state: AgentState) -> str:
        query = state.query.strip()
        memory = state.memory or {}
        facts = memory.get("facts", {})
        last_subject = facts.get("last_project") or facts.get("last_company")
        if last_subject and self._looks_like_follow_up(query):
            return f"{query}. Context: related to {last_subject}."

        if state.context.get("focus_subject"):
            return f"{query}. Context: related to {state.context['focus_subject']}."

        return query

    @staticmethod
    def _looks_like_follow_up(query: str) -> bool:
        lowered = query.lower()
        if len(lowered.split()) <= 4:
            return True
        return any(token in lowered for token in FOLLOW_UP_TOKENS)

    def _build_metadata(self, payload: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        metadata = payload.get("metadata", {}).copy()
        metadata.update(
            {
                "agent": self.config.name,
                "confidence": self._estimate_confidence(payload),
            }
        )
        return metadata

    @staticmethod
    def _extract_sources(payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        results = payload.get("retrieval_results", [])
        sources: List[Dict[str, Any]] = []
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

    @staticmethod
    def _estimate_confidence(payload: Dict[str, Any]) -> float:
        results = payload.get("retrieval_results", [])
        if not results:
            return 0.0
        top_score = results[0].get("score")
        return float(top_score) if top_score is not None else 0.0

    def _update_memory(self, state: AgentState, payload: Dict[str, Any]) -> None:
        memory = state.memory or {}
        facts = memory.setdefault("facts", {})

        primary_subject = self._infer_primary_subject(payload)
        if primary_subject:
            facts["last_project"] = primary_subject

        history: List[Dict[str, Any]] = memory.setdefault("history", [])
        history.append({"role": "user", "content": state.query})
        if state.rag_response and state.rag_response.answer:
            history.append({"role": "assistant", "content": state.rag_response.answer})
        # Keep last 12 turns to avoid unbounded growth
        if len(history) > 24:
            del history[: len(history) - 24]

        memory["facts"] = facts
        memory["history"] = history
        state.memory = memory

    @staticmethod
    def _infer_primary_subject(payload: Dict[str, Any]) -> Optional[str]:
        results = payload.get("retrieval_results", [])
        if not results:
            return None
        metadata = results[0].get("metadata", {})
        return metadata.get("project_name") or metadata.get("company_id")

    def _maybe_switch_collection(self, state: AgentState) -> None:
        collection_name = state.context.get("collection") if state.context else None
        if not collection_name:
            return

        orchestrator = getattr(self.answer_generator, "retrieval_orchestrator", None)
        if not orchestrator:
            return

        retriever = getattr(orchestrator, "retriever", None)
        if retriever and hasattr(retriever, "switch_collection"):
            try:
                retriever.switch_collection(collection_name)
            except Exception:
                # Swallow errors so routing fallback still produces an answer
                pass


def build_rag_agent(**kwargs: Any) -> RAGAgent:
    """Factory for dependency injection."""
    return RAGAgent(**kwargs)
