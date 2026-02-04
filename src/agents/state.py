"""Agent state for the job-search orchestrator graph."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from src.schema.profile import CandidateProfile


class AgentState(TypedDict, total=False):
    """State passed between graph nodes."""

    user_prompt: str
    resume_path: str
    profile: CandidateProfile | None
    search_queries: list[str]
    messages: Annotated[list, add_messages]
