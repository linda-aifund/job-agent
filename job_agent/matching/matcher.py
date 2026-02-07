"""Matcher facade: picks scoring strategy based on config."""

import logging

from job_agent.config import AppConfig
from job_agent.jobs.models import JobListing
from job_agent.matching.keyword_matcher import score_job as keyword_score
from job_agent.matching.ai_matcher import score_job_with_ai
from job_agent.profile.models import ProfileData

logger = logging.getLogger("job_agent.matching")


def score_and_filter_jobs(
    profile: ProfileData,
    jobs: list[JobListing],
    config: AppConfig,
) -> list[JobListing]:
    """Score all jobs and return those above the threshold, sorted by score descending."""
    use_ai = config.matching.use_ai_matching and config.api_keys.openai_api_key
    threshold = config.matching.score_threshold
    ai_pre_filter = config.matching.ai_pre_filter_threshold

    if use_ai:
        logger.info("Using AI matching with keyword pre-filter at %.2f", ai_pre_filter)
    else:
        logger.info("Using keyword matching with threshold %.2f", threshold)

    matched = []

    for job in jobs:
        # Always compute keyword score first
        kw_score, kw_reason = keyword_score(profile, job)

        if use_ai and kw_score >= ai_pre_filter:
            # Try AI matching for jobs that pass keyword pre-filter
            try:
                ai_score, ai_reason = score_job_with_ai(
                    profile, job, config.api_keys.openai_api_key
                )
                job.match_score = ai_score
                job.match_reason = ai_reason
            except Exception:
                # Fall back to keyword score on any AI error
                job.match_score = kw_score
                job.match_reason = kw_reason
        else:
            job.match_score = kw_score
            job.match_reason = kw_reason

        if job.match_score >= threshold:
            matched.append(job)

    # Sort by score descending
    matched.sort(key=lambda j: j.match_score, reverse=True)

    logger.info(
        "Matched %d/%d jobs above threshold %.2f",
        len(matched), len(jobs), threshold,
    )

    return matched
