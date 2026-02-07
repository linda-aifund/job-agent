"""Profile data model."""

from dataclasses import dataclass, field


@dataclass
class ProfileData:
    """Represents a candidate's parsed profile."""

    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: set[str] = field(default_factory=set)
    job_titles: list[str] = field(default_factory=list)
    experience_years: int = 0
    education: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    raw_text: str = ""

    def to_summary_string(self) -> str:
        """Create a concise text summary for AI matching."""
        parts = []
        if self.name:
            parts.append(f"Name: {self.name}")
        if self.job_titles:
            parts.append(f"Titles: {', '.join(self.job_titles)}")
        if self.skills:
            parts.append(f"Skills: {', '.join(sorted(self.skills))}")
        if self.experience_years:
            parts.append(f"Experience: {self.experience_years} years")
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.summary:
            parts.append(f"Summary: {self.summary[:500]}")
        return "\n".join(parts)
