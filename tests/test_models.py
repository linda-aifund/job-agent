"""Tests for data models."""

from job_agent.jobs.models import JobListing
from job_agent.profile.models import ProfileData


class TestJobListing:
    def test_job_id_deterministic(self):
        job = JobListing(title="Software Engineer", company="Acme Inc", url="https://example.com/job/1")
        id1 = job.job_id
        id2 = job.job_id
        assert id1 == id2

    def test_job_id_unique_for_different_jobs(self):
        job1 = JobListing(title="Software Engineer", company="Acme Inc", url="https://example.com/job/1")
        job2 = JobListing(title="Software Engineer", company="Other Corp", url="https://example.com/job/2")
        assert job1.job_id != job2.job_id

    def test_job_id_case_insensitive(self):
        job1 = JobListing(title="Software Engineer", company="Acme Inc", url="https://example.com")
        job2 = JobListing(title="software engineer", company="acme inc", url="https://example.com")
        assert job1.job_id == job2.job_id

    def test_to_dict(self):
        job = JobListing(
            title="Software Engineer",
            company="Acme Inc",
            url="https://example.com",
            location="SF, CA",
            source="serpapi",
        )
        d = job.to_dict()
        assert d["title"] == "Software Engineer"
        assert d["company"] == "Acme Inc"
        assert d["source"] == "serpapi"
        assert "job_id" in d


class TestProfileData:
    def test_to_summary_string(self):
        profile = ProfileData(
            name="John Doe",
            skills={"python", "java"},
            job_titles=["Software Engineer"],
            experience_years=5,
        )
        summary = profile.to_summary_string()
        assert "John Doe" in summary
        assert "Software Engineer" in summary
        assert "5 years" in summary

    def test_empty_profile_summary(self):
        profile = ProfileData()
        summary = profile.to_summary_string()
        assert summary == ""
