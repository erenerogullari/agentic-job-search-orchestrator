"""Graph nodes for the job-search orchestrator."""

import logging

from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.state import AgentState
from src.chains.prompts import (
    PROFILE_EXTRACTION_PROMPT,
    QUERY_GENERATION_PROMPT,
    RELEVANCE_SCORING_PROMPT,
)
from src.schema.profile import CandidateProfile
from src.schema.search import SearchQueryList
from src.schema.job import JobListing
from src.schema.evaluation import JobScore, JobScoreBatch
from src.tools.linkedin_scraper import LinkedInScraper
from src.utils.storage import JobDatabase


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def profile_encoder_node(state: AgentState) -> dict:
    """
    Load resume from PDF, merge with user_prompt, and extract a structured
    CandidateProfile using Gemini 2.5.
    """
    resume_path = state.get("resume_path") or ""
    user_prompt = state.get("user_prompt") or ""

    resume_text = ""
    if resume_path:
        loader = PyPDFLoader(resume_path)
        docs = loader.load()
        resume_text = "\n\n".join(doc.page_content for doc in docs)

    logger.debug(f"Resume text: {resume_text}")

    prompt = PROFILE_EXTRACTION_PROMPT.format(
        resume_text=resume_text or "(No resume provided.)",
        user_prompt=user_prompt or "(No additional preferences.)",
    )

    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = model.with_structured_output(CandidateProfile)
    profile = structured_llm.invoke(prompt)

    logger.debug(f"Profile: {profile}")

    return {"profile": profile}


def query_optimizer_node(state: AgentState) -> dict:
    """
    Generate 4-5 distinct LinkedIn search queries from the candidate profile
    using Gemini 2.5. Combines job titles, location preferences, and keywords.
    """
    profile = state.get("profile")
    if not profile:
        return {"search_queries": []}

    prompt = QUERY_GENERATION_PROMPT.format(
        technical_skills=", ".join(profile.technical_skills) or "(none)",
        experience_level=profile.experience_level or "(unspecified)",
        must_haves=", ".join(profile.must_haves) or "(none)",
        location=profile.location or "(unspecified)",
        summary=profile.summary or "(none)",
    )

    logger.debug(f"Prompt: {prompt}")

    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = model.with_structured_output(SearchQueryList)
    result = structured_llm.invoke(prompt)

    logger.debug(f"Result: {result}")

    return {"search_queries": result.queries}


def job_discovery_node(state: AgentState) -> dict:
    search_queries = state.get("search_queries") or []
    if not search_queries:
        return {"found_jobs": []}

    profile = state.get("profile")
    location = ""
    if profile and profile.location:
        location = profile.location

    job_type_filters = state.get("job_type_filters") or []
    experience_level_filters = state.get("experience_level_filters") or []
    remote_filters = state.get("remote_filters") or []
    remote_value = remote_filters[0] if len(remote_filters) == 1 else ""

    db = JobDatabase(remote=remote_value)
    scraper = LinkedInScraper()

    found_jobs: list[JobListing] = []
    seen_urls: set[str] = set()

    for query in search_queries:
        jobs = scraper.search_jobs(
            query=query,
            location=location,
            job_type=job_type_filters or None,
            experience_level=experience_level_filters or None,
            remote=remote_filters or None,
        )
        if not jobs:
            continue

        urls = [job.job_url for job in jobs if job.job_url]
        new_urls = set(db.get_new_jobs(urls))
        filtered_jobs = [job for job in jobs if job.job_url in new_urls]
        if filtered_jobs:
            db.add_jobs(filtered_jobs)

        for job in filtered_jobs:
            if job.job_url in seen_urls:
                continue
            seen_urls.add(job.job_url)
            found_jobs.append(job)

    return {"found_jobs": found_jobs}


def _format_jobs_block(
    jobs: list[JobListing],
    descriptions: dict[str, str],
) -> str:
    """Format a batch of jobs into a markdown block for the scoring prompt."""
    parts: list[str] = []
    for job in jobs:
        desc = descriptions.get(job.id) or job.description or "(no description available)"
        # Truncate long descriptions to keep prompt size manageable
        if len(desc) > 3000:
            desc = desc[:3000] + "..."
        parts.append(
            f"### Job ID: {job.id}\n"
            f"- **Title:** {job.title or 'N/A'}\n"
            f"- **Company:** {job.company or 'N/A'}\n"
            f"- **Location:** {job.location or 'N/A'}\n"
            f"- **Description:**\n{desc}\n"
        )
    return "\n".join(parts)


def relevance_scorer_node(state: AgentState) -> dict:
    """Score discovered jobs against the candidate profile using Gemini 2.5.

    Three internal phases:
    A. Scrape full job descriptions from LinkedIn detail pages
    B. Score jobs in batches of 5 via LLM structured output
    C. Persist scores to SQLite
    """
    found_jobs = state.get("found_jobs") or []
    profile = state.get("profile")
    if not found_jobs or not profile:
        return {"scored_jobs": []}

    remote_filters = state.get("remote_filters") or []
    remote_value = remote_filters[0] if len(remote_filters) == 1 else ""

    # A. Scrape full descriptions
    scraper = LinkedInScraper()
    descriptions = scraper.scrape_job_descriptions(found_jobs)
    logger.debug(f"Scraped {len(descriptions)} full descriptions out of {len(found_jobs)} jobs")

    # B. Score in batches of 5
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = model.with_structured_output(JobScoreBatch)

    all_scores: list[JobScore] = []
    batch_size = 5

    for i in range(0, len(found_jobs), batch_size):
        batch = found_jobs[i : i + batch_size]
        jobs_block = _format_jobs_block(batch, descriptions)

        prompt = RELEVANCE_SCORING_PROMPT.format(
            technical_skills=", ".join(profile.technical_skills) or "(none)",
            soft_skills=", ".join(profile.soft_skills) or "(none)",
            experience_level=profile.experience_level or "(unspecified)",
            must_haves=", ".join(profile.must_haves) or "(none)",
            location=profile.location or "(unspecified)",
            summary=profile.summary or "(none)",
            jobs_block=jobs_block,
        )

        try:
            result = structured_llm.invoke(prompt)
            all_scores.extend(result.scores)
            logger.debug(f"Scored batch {i // batch_size + 1}: {len(result.scores)} scores")
        except Exception as e:
            logger.error(f"Failed to score batch {i // batch_size + 1}: {e}")
            continue

    # C. Persist scores
    db = JobDatabase(remote=remote_value)
    score_tuples = [(s.job_id, s.relevance_score) for s in all_scores]
    updated = db.update_scores(score_tuples)
    logger.debug(f"Persisted {updated} scores to DB")

    return {"scored_jobs": all_scores}


if __name__ == "__main__":
    """Test the nodes."""
    from dotenv import load_dotenv
    load_dotenv()

    state: AgentState = {
        "user_prompt": "I want entry-level ML roles in germany, ideally remote.",
        "resume_path": "data/resume.pdf",
    }

    # Ingestion phase
    state.update(profile_encoder_node(state))
    print("Profile:")
    for k, v in state.get("profile").model_dump().items():
        print(f"  {k}: {v}")

    # Strategy phase
    state.update(query_optimizer_node(state))
    print("\nSearch Queries:")
    for q in state.get("search_queries"):
        print(f"  - {q}")

    # Discovery phase
    state.update(job_discovery_node(state))
    print(f"\nDiscovered {len(state.get('found_jobs', []))} jobs")

    # Evaluation phase
    state.update(relevance_scorer_node(state))
    scored = state.get("scored_jobs", [])
    print(f"\nScored {len(scored)} jobs:")
    for s in sorted(scored, key=lambda x: x.relevance_score, reverse=True):
        print(f"  [{s.relevance_score:3d}] {s.job_id} — {s.reasoning}")
