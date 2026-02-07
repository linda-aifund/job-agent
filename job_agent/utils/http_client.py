"""HTTP client with retry logic and User-Agent rotation."""

import logging
import random
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("job_agent.http")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


def create_session(max_retries: int = 3, backoff_factor: float = 1.0) -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()

    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    return session


def safe_get(
    url: str,
    session: Optional[requests.Session] = None,
    timeout: int = 30,
    **kwargs,
) -> Optional[requests.Response]:
    """Perform a GET request, returning None on failure instead of raising."""
    if session is None:
        session = create_session()

    try:
        # Rotate User-Agent per request
        session.headers["User-Agent"] = random.choice(USER_AGENTS)
        response = session.get(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.warning("HTTP request failed for %s: %s", url, e)
        return None
