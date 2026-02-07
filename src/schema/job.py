"""Job listing schema for discovered roles."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class JobListing(BaseModel):
    """Structured representation of a single job listing discovered online."""

    id: str = Field(
        ...,
        description="Stable identifier for the job, derived as a hash of the job URL.",
    )
    title: Optional[str] = Field(
        default=None,
        description="Job title as displayed on the job listing.",
    )
    company: Optional[str] = Field(
        default=None,
        description="Company name for the job listing.",
    )
    job_url: str = Field(
        ...,
        description="Canonical URL to the job posting.",
    )
    location: Optional[str] = Field(
        default=None,
        description="Location string for the job (city, region, remote, etc.).",
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional short description or snippet for the job listing.",
    )
    date_posted: Optional[date] = Field(
        default=None,
        description="Date the job was posted, if it can be parsed.",
    )

