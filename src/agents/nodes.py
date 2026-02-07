"""Graph nodes for the job-search orchestrator."""

import logging

from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.state import AgentState
from src.chains.prompts import PROFILE_EXTRACTION_PROMPT, QUERY_GENERATION_PROMPT
from src.schema.profile import CandidateProfile
from src.schema.search import SearchQueryList
from src.schema.job import JobListing
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


if __name__ == "__main__":
    """Test the nodes."""
    from dotenv import load_dotenv
    load_dotenv()

    state : AgentState = {
        "user_prompt": "I want entry-level ML roles in germany, ideally remote.",
        "resume_path": "data/resume.pdf"
    }

    # Ingestion phase
    state.update(profile_encoder_node(state))
    print("Profile:")
    for k, v in state.get("profile").model_dump().items():
        print(f"{k}: {v}")

    # Strategy Phase
    state.update(query_optimizer_node(state))
    print("Search Queries:")
    for q in state.get("search_queries"):
        print(f"- {q}")
