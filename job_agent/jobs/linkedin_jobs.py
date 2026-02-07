"""LinkedIn Jobs scraping (secondary source)."""

import logging
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from job_agent.jobs.models import JobListing
from job_agent.utils.http_client import create_session, safe_get

logger = logging.getLogger("job_agent.jobs.linkedin")

LINKEDIN_JOBS_BASE = "https://www.linkedin.com/jobs/search"


def fetch_linkedin_jobs(
    query: str,
    location: str = "Silicon Valley, CA",
    max_results: int = 50,
) -> list[JobListing]:
    """Scrape job listings from LinkedIn Jobs public search.

    Note: LinkedIn public job search pages are accessible without login.
    Results may be limited compared to authenticated access.
    """
    jobs = []
    session = create_session()
    start = 0

    while len(jobs) < max_results:
        url = (
            f"{LINKEDIN_JOBS_BASE}?"
            f"keywords={quote_plus(query)}"
            f"&location={quote_plus(location)}"
            f"&start={start}"
        )

        response = safe_get(url, session=session)
        if response is None:
            logger.warning("Failed to fetch LinkedIn Jobs page at start=%d", start)
            break

        new_jobs = _parse_linkedin_jobs_page(response.text)
        if not new_jobs:
            break

        jobs.extend(new_jobs)
        start += 25  # LinkedIn paginates in groups of 25

    logger.info("Fetched %d jobs from LinkedIn for query '%s'", len(jobs), query)
    return jobs[:max_results]


def _parse_linkedin_jobs_page(html: str) -> list[JobListing]:
    """Parse a LinkedIn Jobs search results page."""
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    # LinkedIn public job cards
    job_cards = soup.find_all("div", class_=re.compile(r"base-card|job-search-card"))

    if not job_cards:
        # Fallback selector
        job_cards = soup.find_all("li", class_=re.compile(r"jobs-search__result"))

    for card in job_cards:
        job = _parse_linkedin_job_card(card)
        if job:
            jobs.append(job)

    return jobs


def _parse_linkedin_job_card(card) -> JobListing | None:
    """Parse a single LinkedIn job card."""
    # Title
    title_elem = card.find("h3", class_=re.compile(r"base-search-card__title"))
    if not title_elem:
        title_elem = card.find("span", class_=re.compile(r"sr-only"))
    title = title_elem.get_text(strip=True) if title_elem else ""

    if not title:
        return None

    # Company
    company_elem = card.find("h4", class_=re.compile(r"base-search-card__subtitle"))
    if not company_elem:
        company_elem = card.find("a", class_=re.compile(r"hidden-nested-link"))
    company = company_elem.get_text(strip=True) if company_elem else "Unknown"

    # URL
    link_elem = card.find("a", class_=re.compile(r"base-card__full-link"))
    if not link_elem:
        link_elem = card.find("a", href=re.compile(r"linkedin.com/jobs/view"))
    url = link_elem["href"] if link_elem and link_elem.get("href") else ""

    # Location
    location_elem = card.find("span", class_=re.compile(r"job-search-card__location"))
    location = location_elem.get_text(strip=True) if location_elem else ""

    # Posted date
    time_elem = card.find("time")
    posted_date = ""
    if time_elem:
        posted_date = time_elem.get("datetime", "") or time_elem.get_text(strip=True)

    # Remote detection
    remote = "remote" in (title + location).lower()

    return JobListing(
        title=title,
        company=company,
        url=url,
        location=location,
        source="linkedin",
        posted_date=posted_date,
        remote=remote,
    )
