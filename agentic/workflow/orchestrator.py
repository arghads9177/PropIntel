"""LangGraph workflow scaffolding."""

from __future__ import annotations

from typing import Any, Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agentic.agents import build_api_agent, build_rag_agent
from agentic.workflow.state import AgentResponse, AgentState, create_initial_state


def _classify_intent(state: AgentState, **_: Any) -> AgentState:
    """Temporary heuristic-based classifier until LLM router is wired."""
    query_lower = state.query.lower()
    if any(keyword in query_lower for keyword in ("price", "booking", "booked")):
        target = "api"
    else:
        target = "rag"
    state.routing = {"target": target, "confidence": 0.5}
    return state


def _aggregate(state: AgentState, **_: Any) -> AgentState:
    """Combine agent outputs into a final response."""
    if state.routing.get("target") == "api" and state.api_response:
        state.final_response = state.api_response
    elif state.routing.get("target") == "rag" and state.rag_response:
        state.final_response = state.rag_response
    else:
        # fallback
        state.final_response = AgentResponse(
            answer="I could not determine an answer with the available agents.",
            metadata={"agent": "orchestrator", "error": "missing_response"},
        )
    return state


def build_agentic_graph() -> Any:
    """Create the LangGraph graph object."""
    rag_agent = build_rag_agent()
    api_agent = build_api_agent()

    graph = StateGraph(AgentState)
    graph.add_node("classify", _classify_intent)
    graph.add_node("rag_agent", rag_agent)
    graph.add_node("api_agent", api_agent)
    graph.add_node("aggregate", _aggregate)

    graph.set_entry_point("classify")

    # Branching edges based on routing decision
    def router(state: AgentState) -> str:
        return state.routing.get("target", "rag")

    graph.add_conditional_edges(
        "classify",
        router,
        {
            "rag": "rag_agent",
            "api": "api_agent",
        },
    )

    graph.add_edge("rag_agent", "aggregate")
    graph.add_edge("api_agent", "aggregate")
    graph.add_edge("aggregate", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


__all__ = ["build_agentic_graph", "create_initial_state"]
