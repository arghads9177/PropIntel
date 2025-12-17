"""CLI-level tests that ensure routing + workflow integration behaves end-to-end."""

from __future__ import annotations

from cli.propintel_cli import PropIntelCLI

from .conftest import GROUND_TRUTH_RAG_ANSWER


def test_cli_invocation_routes_between_agents(workflow_graph, workflow_config):
    cli = PropIntelCLI()
    cli.workflow = workflow_graph
    cli.workflow_memory = {}
    cli._workflow_config = workflow_config

    rag_result, rag_routing = cli._invoke_workflow("Tell me about Astha's service areas")
    assert rag_routing["target"] == "rag"
    assert GROUND_TRUTH_RAG_ANSWER in rag_result["answer"]

    api_result, api_routing = cli._invoke_workflow("How many flats are available right now?")
    assert api_routing["target"] == "api"
    assert "SHIVALAYA currently has 5 Flats available" in api_result["answer"]

    hybrid_result, hybrid_routing = cli._invoke_workflow(
        "Tell me about Astha and show current available flats in Bandel"
    )
    assert hybrid_routing["target"] == "both"
    assert GROUND_TRUTH_RAG_ANSWER in hybrid_result["answer"]
    assert "Bandel" in hybrid_result["answer"]
