"""Evaluation schema for relevance scoring of job listings."""

from pydantic import BaseModel, Field


class JobScore(BaseModel):
    """Relevance score for a single job listing against a candidate profile."""

    job_id: str = Field(
        ...,
        description="The unique identifier of the job listing being scored.",
    )
    relevance_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall relevance score from 0 (no match) to 100 (perfect match).",
    )
    reasoning: str = Field(
        default="",
        description="One-sentence justification for the score.",
    )


class JobScoreBatch(BaseModel):
    """Batch of relevance scores returned by the LLM for a group of jobs."""

    scores: list[JobScore] = Field(
        default_factory=list,
        description="List of relevance scores, one per job in the batch.",
    )
