"""Public LinkedIn profile scraping for profile extraction."""

import logging
import re

from bs4 import BeautifulSoup

from job_agent.profile.models import ProfileData
from job_agent.utils.http_client import safe_get, create_session
from job_agent.utils.text_processing import extract_keywords, extract_skills

logger = logging.getLogger("job_agent.profile.linkedin")


def scrape_linkedin_profile(linkedin_url: str) -> ProfileData:
    """Scrape a public LinkedIn profile page.

    Note: LinkedIn heavily restricts scraping. This works only on public profiles
    and may break if LinkedIn changes their HTML structure. For production use,
    consider the LinkedIn API or manual profile entry.
    """
    if "linkedin.com/in/" not in linkedin_url:
        raise ValueError(f"Invalid LinkedIn profile URL: {linkedin_url}")

    session = create_session()
    response = safe_get(linkedin_url, session=session)

    if response is None:
        raise ConnectionError(
            f"Failed to fetch LinkedIn profile: {linkedin_url}. "
            "LinkedIn may be blocking the request. Consider using a resume file instead."
        )

    soup = BeautifulSoup(response.text, "lxml")
    return _parse_linkedin_html(soup, linkedin_url)


def _parse_linkedin_html(soup: BeautifulSoup, url: str) -> ProfileData:
    """Parse LinkedIn public profile HTML into ProfileData."""
    profile = ProfileData()

    # Extract name
    name_elem = soup.find("h1")
    if name_elem:
        profile.name = name_elem.get_text(strip=True)

    # Extract headline (usually contains current title)
    headline_elem = soup.find("div", class_=re.compile(r"headline|top-card-layout__headline"))
    if headline_elem:
        headline = headline_elem.get_text(strip=True)
        profile.job_titles = [headline]
        profile.summary = headline

    # Extract location
    location_elem = soup.find("span", class_=re.compile(r"location|top-card-layout__first-subline"))
    if location_elem:
        profile.location = location_elem.get_text(strip=True)

    # Extract about section
    about_section = soup.find("section", class_=re.compile(r"about|summary"))
    if about_section:
        about_text = about_section.get_text(strip=True)
        profile.summary = about_text[:1000]

    # Gather all visible text for skill/keyword extraction
    all_text = soup.get_text(separator=" ", strip=True)
    profile.raw_text = all_text
    profile.skills = extract_skills(all_text)
    profile.keywords = extract_keywords(all_text)

    # Extract experience entries for titles
    experience_section = soup.find("section", id=re.compile(r"experience"))
    if experience_section:
        title_elems = experience_section.find_all("h3")
        for elem in title_elems[:5]:
            title = elem.get_text(strip=True)
            if title and title not in profile.job_titles:
                profile.job_titles.append(title)

    logger.info(
        "Scraped LinkedIn profile: %s (%d skills found)",
        profile.name or "Unknown",
        len(profile.skills),
    )

    return profile
