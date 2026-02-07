"""OpenAI semantic matching (optional, requires API key)."""

import json
import logging
from typing import Optional

from job_agent.jobs.models import JobListing
from job_agent.profile.models import ProfileData

logger = logging.getLogger("job_agent.matching.ai")


def score_job_with_ai(
    profile: ProfileData,
    job: JobListing,
    api_key: str,
) -> tuple[float, str]:
    """Score a job using OpenAI for semantic matching.

    Returns (score, reason) where score is 0.0-1.0.
    Raises on API errors so caller can fall back to keyword matching.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package required for AI matching. Install with: pip install openai")

    client = OpenAI(api_key=api_key)

    profile_summary = profile.to_summary_string()

    job_summary = (
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location}\n"
        f"Description: {job.description[:1500]}"
    )

    prompt = (
        "You are a job matching assistant. Score how well this candidate matches this job posting.\n\n"
        f"CANDIDATE PROFILE:\n{profile_summary}\n\n"
        f"JOB POSTING:\n{job_summary}\n\n"
        "Respond with ONLY a JSON object (no markdown) containing:\n"
        '- "score": a float from 0.0 to 1.0 (1.0 = perfect match)\n'
        '- "reason": a brief explanation (max 100 chars)\n\n'
        "Consider: skills match, experience level, role alignment, and location compatibility."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150,
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(content)
        score = float(result.get("score", 0.0))
        reason = str(result.get("reason", "AI scored"))

        # Clamp score
        score = max(0.0, min(1.0, score))

        logger.debug(
            "AI scored '%s' at %s: %.2f (%s)",
            job.title, job.company, score, reason,
        )

        return round(score, 3), f"[AI] {reason}"

    except json.JSONDecodeError as e:
        logger.warning("Failed to parse AI response as JSON: %s", e)
        raise
    except Exception as e:
        logger.warning("AI matching failed for '%s': %s", job.title, e)
        raise
