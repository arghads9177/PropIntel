"""Heuristic router for deciding which agents should run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agentic.agents.api_models import APIIntent, infer_api_intent


@dataclass
class RoutingDecision:
    """Structured output returned by the heuristic router."""

    target: str = "rag"
    confidence: float = 0.3
    intents: List[str] = field(default_factory=list)
    rationale: str = ""
    source: str = "heuristic"
    hints: Dict[str, Any] = field(default_factory=dict)


class HeuristicRouter:
    """Keyword-based router that prefers deterministic decisions over LLM calls."""

    RAG_KEYWORDS = {
        "amenities",
        "overview",
        "brochure",
        "specs",
        "specification",
        "location",
        "builder",
        "history",
        "company",
        "document",
        "explain",
        "tell me",
    }
    CONTEXTUAL_TOKENS = {"also", "along", "along with", "besides", "plus"}

    def route(self, query: str, memory: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        normalized = (query or "").strip()
        if not normalized:
            return RoutingDecision(
                rationale="Empty query provided; defaulting to RAG",
                hints={"reason": "empty_query"},
            )

        lowered = normalized.lower()
        api_intent = infer_api_intent(lowered)
        wants_api = api_intent != APIIntent.UNKNOWN
        rag_hits = self._extract_hits(lowered, self.RAG_KEYWORDS)
        wants_rag = bool(rag_hits)

        if not wants_rag:
            wants_rag = self._looks_like_contextual(lowered, memory)

        needs_both = wants_api and wants_rag
        rationale_segments: List[str] = []

        if needs_both:
            rationale_segments.append("Query mixes knowledge + live data keywords")
            rationale_segments.append(f"API intent: {api_intent.name}")
            rationale_segments.append(f"RAG cues: {', '.join(rag_hits) or 'contextual follow-up'}")
            return RoutingDecision(
                target="both",
                confidence=0.82,
                intents=[api_intent.name, "RAG_CONTEXT"],
                rationale="; ".join(rationale_segments),
                hints={"api_intent": api_intent.name, "rag_hits": rag_hits},
            )

        if wants_api:
            rationale_segments.append(f"Detected API intent: {api_intent.name}")
            return RoutingDecision(
                target="api",
                confidence=0.75,
                intents=[api_intent.name],
                rationale="; ".join(rationale_segments),
                hints={"api_intent": api_intent.name},
            )

        if wants_rag:
            rationale_segments.append(f"Detected narrative keywords: {', '.join(rag_hits) or 'follow-up context'}")
            return RoutingDecision(
                target="rag",
                confidence=0.7,
                intents=["RAG_CONTEXT"] if rag_hits else [],
                rationale="; ".join(rationale_segments),
                hints={"rag_hits": rag_hits},
            )

        return RoutingDecision(
            target="rag",
            confidence=0.35,
            intents=[],
            rationale="Low signal in heuristics; falling back to default RAG",
            hints={"reason": "low_signal"},
        )

    def _looks_like_contextual(self, lowered: str, memory: Optional[Dict[str, Any]]) -> bool:
        if any(token in lowered for token in self.CONTEXTUAL_TOKENS):
            return True
        if not memory:
            return False
        history = memory.get("history", [])
        if history and len(lowered.split()) <= 5:
            return True
        return False

    @staticmethod
    def _extract_hits(text: str, keywords: set[str]) -> List[str]:
        return [kw for kw in keywords if kw in text]


__all__ = ["HeuristicRouter", "RoutingDecision"]
