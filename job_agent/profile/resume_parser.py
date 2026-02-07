"""PDF and text resume parsing."""

import logging
import re
from pathlib import Path

from job_agent.profile.models import ProfileData
from job_agent.utils.text_processing import extract_keywords, extract_skills, extract_years_experience

logger = logging.getLogger("job_agent.profile")


def parse_resume(file_path: str) -> ProfileData:
    """Parse a resume file (PDF, TXT, or MD) into a ProfileData object."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _extract_pdf_text(path)
    elif suffix in (".txt", ".md", ".markdown"):
        text = path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported resume format: {suffix} (supported: .pdf, .txt, .md)")

    if not text.strip():
        raise ValueError(f"Resume file is empty or unreadable: {file_path}")

    return _parse_text_to_profile(text)


def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise ImportError("PyPDF2 is required for PDF parsing. Install with: pip install PyPDF2")

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def _parse_text_to_profile(text: str) -> ProfileData:
    """Extract structured profile data from raw text."""
    profile = ProfileData(raw_text=text)

    # Extract email
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if email_match:
        profile.email = email_match.group(0)

    # Extract phone
    phone_match = re.search(
        r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text
    )
    if phone_match:
        profile.phone = phone_match.group(0)

    # Extract name (heuristic: first non-empty line that looks like a name)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines[:5]:
        # A name line is typically short, has no special chars, and is mostly title case
        if (
            len(line) < 60
            and not re.search(r"[@|•·]", line)
            and re.match(r"^[A-Z][a-z]+(?: [A-Z][a-z]+)+$", line)
        ):
            profile.name = line
            break

    # Extract skills
    profile.skills = extract_skills(text)

    # Extract keywords
    profile.keywords = extract_keywords(text)

    # Extract years of experience
    years = extract_years_experience(text)
    if years is not None:
        profile.experience_years = years

    # Try to extract job titles from common section patterns
    profile.job_titles = _extract_job_titles(text)

    # Extract summary (first paragraph-like block after name/contact)
    profile.summary = _extract_summary(text)

    logger.info(
        "Parsed resume: %d skills, %d keywords, %d years experience",
        len(profile.skills),
        len(profile.keywords),
        profile.experience_years,
    )

    return profile


def _extract_job_titles(text: str) -> list[str]:
    """Extract job titles from resume text."""
    titles = []
    # Look for patterns like "Software Engineer at Company" or "Title | Company"
    patterns = [
        r"(?:^|\n)\s*([\w\s]+(?:engineer|developer|architect|manager|analyst|designer|scientist|lead|director|consultant))\s*(?:at|@|\||-|–)\s*\w",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            title = match.strip()
            if 3 < len(title) < 60:
                titles.append(title)

    # Deduplicate while preserving order
    seen = set()
    unique_titles = []
    for t in titles:
        t_lower = t.lower()
        if t_lower not in seen:
            seen.add(t_lower)
            unique_titles.append(t)

    return unique_titles[:5]  # Cap at 5 titles


def _extract_summary(text: str) -> str:
    """Extract a summary/objective section from resume text."""
    # Look for explicit summary/objective section
    patterns = [
        r"(?:summary|objective|about|profile)\s*[:|\n]\s*(.+?)(?:\n\s*\n|\n[A-Z]{2,})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            summary = match.group(1).strip()
            if 20 < len(summary) < 1000:
                return summary

    # Fallback: first paragraph after contact info (skip first 3 lines)
    lines = text.split("\n")
    para_lines = []
    started = False
    for line in lines[3:]:
        stripped = line.strip()
        if stripped and not re.search(r"[@|•·\d{3}]", stripped):
            started = True
            para_lines.append(stripped)
        elif started and not stripped:
            break

    if para_lines:
        summary = " ".join(para_lines)
        if 20 < len(summary) < 1000:
            return summary

    return ""
