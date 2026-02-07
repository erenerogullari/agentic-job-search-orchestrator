"""Schema for search queries."""

from typing import List
from pydantic import BaseModel, Field


class SearchQueryList(BaseModel):
    """Structured list of LinkedIn-style search queries for job search."""

    queries: List[str] = Field(
        default_factory=list,
        description="4-5 distinct search query strings (e.g. 'AI Engineer remote Germany', 'Machine Learning Engineer Berlin python').",
    )