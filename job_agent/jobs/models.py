"""Job listing data model."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class JobListing:
    """Represents a job listing from any source."""

    title: str
    company: str
    url: str
    location: str = ""
    description: str = ""
    salary: str = ""
    source: str = ""  # "serpapi", "indeed", "linkedin"
    posted_date: str = ""
    job_type: str = ""  # full-time, part-time, contract
    remote: bool = False
    match_score: float = 0.0
    match_reason: str = ""
    fetched_at: datetime = field(default_factory=datetime.now)

    @property
    def job_id(self) -> str:
        """Generate a unique ID via SHA-256 of (title, company, url)."""
        raw = f"{self.title.strip().lower()}|{self.company.strip().lower()}|{self.url.strip().lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "location": self.location,
            "description": self.description,
            "salary": self.salary,
            "source": self.source,
            "posted_date": self.posted_date,
            "job_type": self.job_type,
            "remote": self.remote,
            "match_score": self.match_score,
            "match_reason": self.match_reason,
        }
