"""Candidate profile schema for resume ingestion and search strategy."""

from typing import List

from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    """Structured profile extracted from resume and user preferences."""

    technical_skills: list[str] = Field(
        default_factory=list,
        description="Technical skills (languages, frameworks, tools) from resume and preferences.",
    )
    soft_skills: list[str] = Field(
        default_factory=list,
        description="Soft skills (communication, teamwork, problem-solving) from resume and preferences.",
    )
    experience_level: str = Field(
        default="",
        description="Experience level (e.g. junior, mid, senior, staff).",
    )
    must_haves: list[str] = Field(
        default_factory=list,
        description="Must-have requirements or preferences from the candidate.",
    )
    location: str = Field(
        default="",
        description="Preferred or current location (city, region, or remote).",
    )
    summary: str = Field(
        default="",
        description="A 2-sentence professional persona summary of the candidate.",
    )


class SearchQueryList(BaseModel):
    """Structured list of LinkedIn-style search queries for job search."""

    queries: List[str] = Field(
        default_factory=list,
        description="4-5 distinct search query strings (e.g. 'AI Engineer remote Germany', 'Machine Learning Engineer Berlin python').",
    )
