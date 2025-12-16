"""LangGraph workflow scaffolding."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agentic.agents import build_api_agent, build_rag_agent
from agentic.workflow.routing import HeuristicRouter, RoutingDecision
from agentic.workflow.state import AgentResponse, AgentState, create_initial_state


INTENT_PROMPT = ChatPromptTemplate.from_template(
    """You are a routing assistant for a property intelligence system.
Analyze the user query and decide which agents should respond.
Respond with JSON containing keys: target (rag|api|both), confidence (0-1 float),
intents (list of strings), rationale.
Query: {query}
Conversation summary: {summary}
Heuristic hints (non-binding): {routing_hints}
"""
)


HEURISTIC_ROUTER = HeuristicRouter()
HEURISTIC_CONFIDENCE_THRESHOLD = 0.65


def _summarize_memory(state: AgentState) -> str:
    history = (state.memory or {}).get("history", [])
    last_turns = history[-4:]
    return " | ".join(f"{item['role']}: {item['content']}" for item in last_turns)


def _decision_to_dict(decision: RoutingDecision) -> Dict[str, Any]:
    return {
        "target": decision.target,
        "confidence": decision.confidence,
        "intents": decision.intents,
        "rationale": decision.rationale,
        "source": decision.source,
        "hints": decision.hints,
    }


def _call_router_llm(state: AgentState, **_: Any) -> AgentState:
    from generation.llm_service import LLMService

    heuristic_decision = HEURISTIC_ROUTER.route(state.query, state.memory)
    heuristic_payload = _decision_to_dict(heuristic_decision)

    if heuristic_decision.confidence >= HEURISTIC_CONFIDENCE_THRESHOLD:
        heuristic_payload["strategy"] = "heuristic"
        state.routing = heuristic_payload
        return state

    summary = _summarize_memory(state)
    hint_text = heuristic_decision.rationale or "No confident heuristic signal."
    prompt = INTENT_PROMPT.format(query=state.query, summary=summary, routing_hints=hint_text)
    llm = LLMService(provider="groq")
    llm_response = llm.generate(
        prompt=prompt,
        system_prompt="You are a strict JSON generator.",
        max_tokens=200,
    )

    try:
        import json

        parsed = json.loads(llm_response.get("answer", "{}"))
        target = parsed.get("target", "rag")
        confidence = float(parsed.get("confidence", 0.5))
        intents = parsed.get("intents", [])
        rationale = parsed.get("rationale", "")
    except Exception:
        target = "rag"
        confidence = 0.3
        intents = []
        rationale = "Failed to parse LLM routing response"

    if confidence < 0.4:
        if heuristic_decision.target in {"api", "both"}:
            target = heuristic_decision.target
            confidence = HEURISTIC_CONFIDENCE_THRESHOLD
            intents = heuristic_decision.intents
            rationale = f"LLM fallback to heuristics: {heuristic_decision.rationale or 'API keywords detected.'}"
        else:
            lower = state.query.lower()
            if any(term in lower for term in ("price", "booking", "booked")):
                target = "api"
                confidence = 0.45
                intents = intents or ["PRICE_LOOKUP"]
                rationale = "Keyword fallback forced API route"
            else:
                target = "rag"

    state.routing = {
        "target": target,
        "confidence": confidence,
        "intents": intents,
        "rationale": rationale,
        "source": "llm",
        "hints": heuristic_payload.get("hints", {}),
        "heuristic_seed": heuristic_payload,
    }
    return state


def _aggregate(state: AgentState, **_: Any) -> AgentState:
    """Combine agent outputs into a final response."""
    target = state.routing.get("target", "rag")
    responses = []
    if target in ("rag", "both") and state.rag_response:
        responses.append(state.rag_response)
    if target in ("api", "both") and state.api_response:
        responses.append(state.api_response)

    if not responses:
        state.final_response = AgentResponse(
            answer="I could not determine an answer with the available agents.",
            metadata={"agent": "orchestrator", "error": "missing_response"},
        )
        return state

    if len(responses) == 1:
        state.final_response = responses[0]
    else:
        combined_answer = "\n\n".join(resp.answer for resp in responses if resp.answer)
        combined_sources = [src for resp in responses for src in resp.sources]
        combined_metadata: Dict[str, Any] = {
            "agent": "aggregator",
            "components": [resp.metadata for resp in responses],
        }
        state.final_response = AgentResponse(
            answer=combined_answer,
            sources=combined_sources,
            metadata=combined_metadata,
        )

    _update_memory_with_final(state)
    return state


def _update_memory_with_final(state: AgentState) -> None:
    memory = state.memory or {}
    history = memory.setdefault("history", [])
    history.append({"role": "user", "content": state.query})
    if state.final_response and state.final_response.answer:
        history.append({"role": "assistant", "content": state.final_response.answer})
    memory["history"] = history[-24:]
    state.memory = memory


def build_agentic_graph(*, rag_agent: Optional[Any] = None, api_agent: Optional[Any] = None) -> Any:
    """Create the LangGraph graph object."""
    rag_agent = rag_agent or build_rag_agent()
    api_agent = api_agent or build_api_agent()

    graph = StateGraph(AgentState)
    graph.add_node("classify", _call_router_llm)
    graph.add_node("rag_agent", rag_agent)
    graph.add_node("api_agent", api_agent)
    graph.add_node("aggregate", _aggregate)

    graph.set_entry_point("classify")

    def router(state: AgentState) -> str:
        target = state.routing.get("target", "rag")
        if target == "both":
            return "rag"
        return target

    graph.add_conditional_edges(
        "classify",
        router,
        {
            "rag": "rag_agent",
            "api": "api_agent",
        },
    )

    def _next_from_rag(state: AgentState) -> str:
        if state.routing.get("target") == "both" and not state.routing.get("api_invoked"):
            state.routing["api_invoked"] = True
            return "api"
        return "aggregate"

    graph.add_conditional_edges(
        "rag_agent",
        _next_from_rag,
        {
            "aggregate": "aggregate",
            "api": "api_agent",
        },
    )

    graph.add_edge("api_agent", "aggregate")
    graph.add_edge("aggregate", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


__all__ = ["build_agentic_graph", "create_initial_state"]
