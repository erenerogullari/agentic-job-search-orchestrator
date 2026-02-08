"""Simple LinkedIn job search scraper used in the discovery phase."""

from __future__ import annotations

from datetime import date, datetime
import hashlib
import os
from typing import List
from urllib.parse import quote_plus, urlencode, urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from src.schema.job import JobListing


JOB_TYPE_MAP = {
    "full-time": "F",
    "part-time": "P",
    "contract": "C",
    "temporary": "T",
    "volunteer": "V",
}
EXPERIENCE_LEVEL_MAP = {
    "internship": "1",
    "entry level": "2",
    "associate": "3",
    "mid-senior level": "4",
    "director": "5",
}
REMOTE_MAP = {
    "on-site": "1",
    "hybrid": "3",
    "remote": "2",
}


def _normalize(values: List[str] | None) -> List[str]:
    if not values:
        return []
    return [v.strip().lower() for v in values if v and v.strip()]


def _canonicalize_job_url(url: str) -> str:
    """Strip query params and fragments for stable job URLs."""
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return url
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


class LinkedInScraper:
    """Scrape LinkedIn job search results using Playwright."""

    def search_jobs(
        self,
        query: str,
        location: str,
        job_type: List[str] | None = None,
        experience_level: List[str] | None = None,
        remote: List[str] | None = None,
        limit: int = 100,
        wait_ms: int = 20000,
    ) -> List[JobListing]:
        """Search LinkedIn jobs for the given query and return JobListing objects."""
        job_type_codes = [
            JOB_TYPE_MAP[v] for v in _normalize(job_type) if v in JOB_TYPE_MAP
        ]
        experience_codes = [
            EXPERIENCE_LEVEL_MAP[v]
            for v in _normalize(experience_level)
            if v in EXPERIENCE_LEVEL_MAP
        ]
        remote_codes = [
            REMOTE_MAP[v] for v in _normalize(remote) if v in REMOTE_MAP
        ]

        params = {
            "keywords": query,
            "location": location,
        }
        if job_type_codes:
            params["f_JT"] = ",".join(job_type_codes)
        if experience_codes:
            params["f_E"] = ",".join(experience_codes)
        if remote_codes:
            params["f_WT"] = ",".join(remote_codes)

        search_url = "https://www.linkedin.com/jobs/search?" + urlencode(
            params, quote_via=quote_plus
        )

        results: List[JobListing] = []

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
            })

            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            except (PlaywrightTimeoutError, PlaywrightError) as e:
                print(f"Navigation failed: {e}")
                browser.close()
                return results

            # Handle "Sign in to view more jobs" modal if it appears
            try:
                modal_close_btn = page.locator("button.modal__dismiss")
                if modal_close_btn.is_visible(timeout=5000):
                    modal_close_btn.click()
                    page.wait_for_timeout(1000)  # Wait for modal to fade
            except Exception:
                pass  # Modal didn't appear or couldn't be closed

            try:
                page.wait_for_selector(
                    "ul.jobs-search__results-list > li", timeout=wait_ms
                )
                cards = page.query_selector_all("ul.jobs-search__results-list > li")
                print(f"Found {len(cards)} cards")
                if not cards:
                    cards = page.query_selector_all("div.base-card")
            except PlaywrightError as e:
                print(f"Error waiting for job cards: {e}")
                browser.close()
                return results

            if not cards:
                try:
                    path = os.path.abspath("linkedin_scraper_debug.png")
                    page.screenshot(path=path)
                    print(f"No job cards found. Screenshot saved to: {path}")
                except Exception as e:
                    print(f"Error saving screenshot: {e}")
                    pass

            try:
                for card in cards:

                    if len(results) >= limit:
                        break

                    title_el = card.query_selector("h3.base-search-card__title")
                    company_el = card.query_selector(
                        "h4.base-search-card__subtitle a, h4.base-search-card__subtitle"
                    )
                    location_el = card.query_selector("span.job-search-card__location")
                    link_el = card.query_selector("a.base-card__full-link")
                    date_el = card.query_selector(
                        "time.job-search-card__listdate, time.job-search-card__listdate--new"
                    )
                    description_el = card.query_selector(
                        "p.job-search-card__snippet, div.base-search-card__metadata p"
                    )

                    title = (title_el.inner_text().strip() if title_el else "") or None
                    company = (company_el.inner_text().strip() if company_el else "") or None
                    print(f"Company: {company}")
                    location_text = (
                        location_el.inner_text().strip() if location_el else ""
                    ) or None
                    job_url = (link_el.get_attribute("href") if link_el else "") or None
                    canonical_url = (
                        _canonicalize_job_url(job_url) if job_url else None
                    )
                    posted_raw = (date_el.get_attribute("datetime") if date_el else None) or (
                        date_el.inner_text().strip() if date_el else ""
                    )
                    description = (
                        description_el.inner_text().strip() if description_el else None
                    )

                    job_id = hashlib.md5(canonical_url.encode("utf-8")).hexdigest()

                    date_posted = None
                    if posted_raw:
                        try:
                            date_posted = date.fromisoformat(posted_raw)
                        except ValueError:
                            try:
                                date_posted = datetime.fromisoformat(
                                    posted_raw.replace("Z", "+00:00")
                                ).date()
                            except ValueError:
                                date_posted = None

                    results.append(
                        JobListing(
                            id=job_id,
                            title=title,
                            company=company,
                            job_url=canonical_url,
                            location=location_text,
                            description=description,
                            date_posted=date_posted,
                        )
                    )
            except PlaywrightError as e:
                print(f"Error scraping job card: {e}")
                browser.close()
                return results

            browser.close()

        return results


    def scrape_job_descriptions(
        self,
        jobs: list[JobListing],
        wait_ms: int = 10000,
    ) -> dict[str, str]:
        """Scrape full job descriptions from LinkedIn detail pages.

        Returns a dict mapping job_id -> description text.
        Gracefully skips jobs that fail to load.
        """
        descriptions: dict[str, str] = {}
        if not jobs:
            return descriptions

        description_selectors = [
            "div.show-more-less-html__markup",
            "div.description__text",
            "section.show-more-less-html",
            "div.jobs-description__content",
        ]

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
            })

            for job in jobs:
                if not job.job_url:
                    continue
                try:
                    page.goto(job.job_url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(wait_ms)

                    description_text = None
                    for selector in description_selectors:
                        try:
                            el = page.query_selector(selector)
                            if el:
                                description_text = el.inner_text().strip()
                                if description_text:
                                    break
                        except PlaywrightError:
                            continue

                    if description_text:
                        descriptions[job.id] = description_text
                        print(f"Scraped description for {job.id} ({job.title})")
                    else:
                        print(f"No description found for {job.id} ({job.title})")

                except (PlaywrightTimeoutError, PlaywrightError) as e:
                    print(f"Failed to scrape {job.id} ({job.title}): {e}")
                    continue

                # Polite delay between pages
                page.wait_for_timeout(1500)

            browser.close()

        return descriptions


if __name__ == "__main__":
    """Test the scraper. Set LINKEDIN_SCRAPER_DEBUG=1 to save a screenshot when no jobs found."""
    from src.utils.storage import JobDatabase
    db = JobDatabase(remote="remote")
    scraper = LinkedInScraper()
    jobs = scraper.search_jobs(
        query="AI Engineer",
        location="Germany",
        job_type=["full-time"],
        experience_level=["entry level"],
        remote=["remote"],
        wait_ms=6000,
    )
    print(f"Found {len(jobs)} jobs:")
    db.add_jobs(jobs)
    print(db.db_to_df())