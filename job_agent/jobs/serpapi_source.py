"""SerpAPI Google Jobs source (primary)."""

import logging
from typing import Optional

from job_agent.jobs.models import JobListing

logger = logging.getLogger("job_agent.jobs.serpapi")


def fetch_serpapi_jobs(
    api_key: str,
    query: str,
    location: str = "Silicon Valley, California",
    max_results: int = 50,
) -> list[JobListing]:
    """Fetch job listings from Google Jobs via SerpAPI."""
    if not api_key:
        logger.warning("SerpAPI key not configured, skipping Google Jobs source")
        return []

    try:
        from serpapi import GoogleSearch
    except ImportError:
        logger.error("google-search-results package not installed")
        return []

    jobs = []
    start = 0
    chips = None

    while len(jobs) < max_results:
        params = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "api_key": api_key,
            "start": start,
        }
        if chips:
            params["chips"] = chips

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
        except Exception as e:
            logger.error("SerpAPI request failed: %s", e)
            break

        job_results = results.get("jobs_results", [])
        if not job_results:
            break

        # Capture chips token for pagination on first request
        if start == 0 and not chips:
            chips_list = results.get("chips", [])
            # No specific chip needed for general search

        for item in job_results:
            job = _parse_serpapi_job(item)
            if job:
                jobs.append(job)

        start += 10  # SerpAPI paginates in groups of 10

        if len(job_results) < 10:
            break  # No more pages

    logger.info("Fetched %d jobs from SerpAPI for query '%s'", len(jobs), query)
    return jobs[:max_results]


def _parse_serpapi_job(item: dict) -> Optional[JobListing]:
    """Parse a single SerpAPI job result into a JobListing."""
    title = item.get("title", "")
    company = item.get("company_name", "")

    if not title or not company:
        return None

    # Build URL - SerpAPI provides apply links or a share link
    url = ""
    apply_options = item.get("apply_options", [])
    if apply_options:
        url = apply_options[0].get("link", "")
    if not url:
        # Fallback: construct a Google Jobs search link
        related_links = item.get("related_links", [])
        if related_links:
            url = related_links[0].get("link", "")
    if not url:
        url = f"https://www.google.com/search?q={title}+{company}+jobs"

    # Extract location
    location = item.get("location", "")

    # Extract description
    description = item.get("description", "")

    # Extract salary if available
    salary = ""
    salary_info = item.get("detected_extensions", {})
    if salary_info.get("salary"):
        salary = salary_info["salary"]

    # Job type
    job_type = ""
    if salary_info.get("schedule_type"):
        job_type = salary_info["schedule_type"]

    # Remote detection
    remote = "remote" in (location + title + description).lower()

    # Posted date
    posted_date = salary_info.get("posted_at", "")

    return JobListing(
        title=title,
        company=company,
        url=url,
        location=location,
        description=description,
        salary=salary,
        source="serpapi",
        posted_date=posted_date,
        job_type=job_type,
        remote=remote,
    )
