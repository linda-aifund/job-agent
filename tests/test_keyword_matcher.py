"""Tests for keyword matching."""

from job_agent.jobs.models import JobListing
from job_agent.matching.keyword_matcher import score_job
from job_agent.profile.models import ProfileData


def make_profile(**kwargs) -> ProfileData:
    defaults = dict(
        name="Test User",
        skills={"python", "java", "docker", "kubernetes", "aws"},
        job_titles=["Software Engineer", "Backend Engineer"],
        experience_years=5,
        keywords=["python", "backend", "microservices", "distributed", "cloud"],
    )
    defaults.update(kwargs)
    return ProfileData(**defaults)


def make_job(**kwargs) -> JobListing:
    defaults = dict(
        title="Software Engineer",
        company="Test Corp",
        url="https://example.com/job",
        description="Looking for a Python developer with experience in Docker and Kubernetes.",
    )
    defaults.update(kwargs)
    return JobListing(**defaults)


class TestKeywordMatcher:
    def test_good_match(self):
        profile = make_profile()
        job = make_job(
            title="Backend Software Engineer",
            description="We need a Python developer with Docker, Kubernetes, and AWS experience. 5 years required.",
        )
        score, reason = score_job(profile, job)
        assert score > 0.4
        assert reason  # Should have some explanation

    def test_poor_match(self):
        profile = make_profile()
        job = make_job(
            title="Product Manager",
            description="Looking for someone to manage product roadmap and stakeholder relationships.",
        )
        score, reason = score_job(profile, job)
        assert score < 0.3

    def test_title_match_boosts_score(self):
        profile = make_profile()
        job_matching_title = make_job(title="Software Engineer")
        job_different_title = make_job(title="Data Scientist")

        score1, _ = score_job(profile, job_matching_title)
        score2, _ = score_job(profile, job_different_title)
        assert score1 > score2

    def test_skills_overlap_matters(self):
        profile = make_profile()
        job_with_skills = make_job(description="Python, Docker, Kubernetes, AWS, Java development")
        job_without_skills = make_job(description="Excellent communication and leadership skills needed")

        score1, _ = score_job(profile, job_with_skills)
        score2, _ = score_job(profile, job_without_skills)
        assert score1 > score2

    def test_score_range(self):
        profile = make_profile()
        job = make_job()
        score, _ = score_job(profile, job)
        assert 0.0 <= score <= 1.0

    def test_empty_profile(self):
        profile = ProfileData()
        job = make_job()
        score, _ = score_job(profile, job)
        assert 0.0 <= score <= 1.0
