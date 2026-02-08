"""Keyword overlap scoring (default, free matcher)."""

import logging

from job_agent.jobs.models import JobListing
from job_agent.profile.models import ProfileData
from job_agent.utils.text_processing import (
    extract_keywords,
    extract_skills,
    extract_years_experience,
    title_similarity,
)

logger = logging.getLogger("job_agent.matching.keyword")

# Scoring weights
WEIGHT_SKILLS = 0.40
WEIGHT_TITLE = 0.30
WEIGHT_KEYWORDS = 0.20
WEIGHT_EXPERIENCE = 0.10


def score_job(profile: ProfileData, job: JobListing) -> tuple[float, str]:
    """Score a job against a profile using keyword overlap.

    Returns (score, reason) where score is 0.0-1.0.
    """
    reasons = []

    # 1. Skills overlap (40%)
    job_text = f"{job.title} {job.description}".lower()
    job_skills = extract_skills(job_text) | {s for s in profile.skills if s in job_text}

    if profile.skills and job_skills:
        overlap = profile.skills & job_skills
        skills_score = len(overlap) / max(len(profile.skills), 1)
        skills_score = min(skills_score, 1.0)
        if overlap:
            reasons.append(f"Skills: {', '.join(sorted(overlap)[:5])}")
    else:
        skills_score = 0.0

    # 2. Title similarity (30%)
    title_score = 0.0
    best_title_match = ""
    search_titles = profile.job_titles if profile.job_titles else []

    for profile_title in search_titles:
        sim = title_similarity(profile_title, job.title)
        if sim > title_score:
            title_score = sim
            best_title_match = profile_title

    if title_score > 0.3:
        reasons.append(f"Title match: {best_title_match}")

    # 3. Keyword overlap (20%)
    job_keywords = set(extract_keywords(job_text, top_n=20))
    profile_keywords = set(profile.keywords[:30])

    if profile_keywords and job_keywords:
        kw_overlap = profile_keywords & job_keywords
        keywords_score = len(kw_overlap) / max(len(profile_keywords), 1)
        keywords_score = min(keywords_score, 1.0)
    else:
        keywords_score = 0.0

    # 4. Experience alignment (10%)
    experience_score = 0.0
    if profile.experience_years > 0:
        job_years = extract_years_experience(job_text)
        if job_years is not None:
            diff = abs(profile.experience_years - job_years)
            if diff <= 2:
                experience_score = 1.0
                reasons.append(f"Experience: {job_years}yr required, you have {profile.experience_years}yr")
            elif diff <= 5:
                experience_score = 0.5
            else:
                experience_score = 0.2
        else:
            # No experience requirement mentioned - neutral
            experience_score = 0.5

    # Weighted total
    total = (
        WEIGHT_SKILLS * skills_score
        + WEIGHT_TITLE * title_score
        + WEIGHT_KEYWORDS * keywords_score
        + WEIGHT_EXPERIENCE * experience_score
    )

    reason = "; ".join(reasons) if reasons else "Low keyword overlap"

    return round(total, 3), reason
