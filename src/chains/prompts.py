"""Prompt templates for the job-search orchestrator."""

PROFILE_EXTRACTION_PROMPT = """You are extracting a structured candidate profile for job matching.

Resume text:
---
{resume_text}
---

Additional preferences or context from the candidate:
---
{user_prompt}
---

Extract and merge the above into a single candidate profile. Populate:
- technical_skills: list of technologies, languages, frameworks, and tools (from resume and any preferences)
- soft_skills: list of communication, teamwork, problem-solving skills (from resume and any preferences)
- experience_level: e.g. "junior", "mid", "senior", "staff" (infer from resume if not stated)
- must_haves: list of must-have job criteria or preferences from the candidate
- location: preferred or current location (city, region, "remote", or similar)
- summary: A 2-sentence professional persona summary of the candidate.

Use empty string or empty list when information is not available. Prefer the candidate's stated preferences when they conflict with resume content.
"""

QUERY_GENERATION_PROMPT = """You are a technical recruiter trying to find relevant jobs for this candidate on LinkedIn.

Candidate profile:
- Technical skills: {technical_skills}
- Experience level: {experience_level}
- Must-haves: {must_haves}
- Location preference: {location}
- Summary: {summary}

Generate exactly 4-5 distinct LinkedIn job search queries that combine:
1. Primary job titles (derive from skills and experience, e.g. "AI Engineer", "Machine Learning Engineer")
2. Location preferences (city, region, or country from the profile)
3. Keywords (key technologies or terms from technical_skills)

Important: If the candidate wants remote work (check location for "remote" or similar), append "remote" to the query string where relevant (e.g. "AI Engineer remote Germany", "Machine Learning Engineer remote python").

Each query should be a single string, suitable for pasting into LinkedIn search. Vary titles, locations, and keyword combinations across the 4-5 queries to cover different angles.
"""

RELEVANCE_SCORING_PROMPT = """You are scoring job listings for relevance to a specific candidate.

Candidate profile:
- Technical skills: {technical_skills}
- Soft skills: {soft_skills}
- Experience level: {experience_level}
- Must-haves: {must_haves}
- Location preference: {location}
- Summary: {summary}

Score each job below on a 0-100 scale using this rubric:
- Technical skill match (0-35): How well do the job's required skills overlap with the candidate's technical skills?
- Experience level fit (0-25): Does the job's seniority match the candidate's experience level?
- Must-haves alignment (0-20): Does the job satisfy the candidate's must-have criteria?
- Location compatibility (0-10): Does the job location match the candidate's location preference (remote, city, etc.)?
- Overall role fit (0-10): How well does the overall role align with the candidate's professional summary and goals?

Jobs to score:
{jobs_block}

Return a score (0-100) and a one-sentence reasoning for each job. Use the job_id exactly as provided.
"""
