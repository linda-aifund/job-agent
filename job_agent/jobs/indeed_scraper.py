"""Indeed job scraping (secondary source)."""

import logging
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from job_agent.jobs.models import JobListing
from job_agent.utils.http_client import create_session, safe_get

logger = logging.getLogger("job_agent.jobs.indeed")

INDEED_BASE = "https://www.indeed.com"


def fetch_indeed_jobs(
    query: str,
    location: str = "Silicon Valley, CA",
    max_results: int = 50,
) -> list[JobListing]:
    """Scrape job listings from Indeed search results."""
    jobs = []
    session = create_session()
    start = 0

    while len(jobs) < max_results:
        url = (
            f"{INDEED_BASE}/jobs?"
            f"q={quote_plus(query)}"
            f"&l={quote_plus(location)}"
            f"&start={start}"
        )

        response = safe_get(url, session=session)
        if response is None:
            logger.warning("Failed to fetch Indeed page at start=%d", start)
            break

        new_jobs = _parse_indeed_page(response.text)
        if not new_jobs:
            break

        jobs.extend(new_jobs)
        start += 10

    logger.info("Fetched %d jobs from Indeed for query '%s'", len(jobs), query)
    return jobs[:max_results]


def _parse_indeed_page(html: str) -> list[JobListing]:
    """Parse an Indeed search results page."""
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    # Indeed uses job cards with data attributes
    job_cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|cardOutline|resultContent"))

    if not job_cards:
        # Fallback: try finding by data-jk attribute (job key)
        job_cards = soup.find_all("a", attrs={"data-jk": True})

    for card in job_cards:
        job = _parse_indeed_card(card)
        if job:
            jobs.append(job)

    return jobs


def _parse_indeed_card(card) -> JobListing | None:
    """Parse a single Indeed job card."""
    # Title
    title_elem = card.find("h2", class_=re.compile(r"jobTitle")) or card.find("a", class_=re.compile(r"jcs-JobTitle"))
    if not title_elem:
        title_elem = card.find("span", attrs={"title": True})

    title = ""
    if title_elem:
        title = title_elem.get_text(strip=True)

    if not title:
        return None

    # Company
    company_elem = card.find("span", attrs={"data-testid": "company-name"})
    if not company_elem:
        company_elem = card.find("span", class_=re.compile(r"company"))
    company = company_elem.get_text(strip=True) if company_elem else "Unknown"

    # URL
    link_elem = card.find("a", href=True)
    url = ""
    if link_elem:
        href = link_elem["href"]
        if href.startswith("/"):
            url = f"{INDEED_BASE}{href}"
        elif href.startswith("http"):
            url = href
        else:
            url = f"{INDEED_BASE}/{href}"

    # Location
    location_elem = card.find("div", attrs={"data-testid": "text-location"})
    if not location_elem:
        location_elem = card.find("div", class_=re.compile(r"companyLocation"))
    location = location_elem.get_text(strip=True) if location_elem else ""

    # Salary
    salary_elem = card.find("div", class_=re.compile(r"salary|estimated-salary"))
    salary = salary_elem.get_text(strip=True) if salary_elem else ""

    # Snippet/description
    snippet_elem = card.find("div", class_=re.compile(r"job-snippet"))
    description = snippet_elem.get_text(strip=True) if snippet_elem else ""

    # Remote detection
    remote = "remote" in (title + location + description).lower()

    return JobListing(
        title=title,
        company=company,
        url=url,
        location=location,
        description=description,
        salary=salary,
        source="indeed",
        remote=remote,
    )
