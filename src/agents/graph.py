"""Compiled LangGraph for the job-search orchestrator."""

from langgraph.graph import END, StateGraph

from src.agents.state import AgentState
from src.agents.nodes import (
    profile_encoder_node,
    query_optimizer_node,
    job_discovery_node,
    relevance_scorer_node,
)


def build_graph():
    """Build and compile the 4-node linear pipeline."""
    graph = StateGraph(AgentState)

    graph.add_node("ingestion", profile_encoder_node)
    graph.add_node("strategy", query_optimizer_node)
    graph.add_node("discovery", job_discovery_node)
    graph.add_node("evaluation", relevance_scorer_node)

    graph.set_entry_point("ingestion")
    graph.add_edge("ingestion", "strategy")
    graph.add_edge("strategy", "discovery")
    graph.add_edge("discovery", "evaluation")
    graph.add_edge("evaluation", END)

    return graph.compile()
