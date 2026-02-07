"""Tests for SQLite database."""

import os
import tempfile

import pytest

from job_agent.jobs.models import JobListing
from job_agent.storage.database import JobDatabase


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        database = JobDatabase(db_path)
        yield database
        database.close()


@pytest.fixture
def sample_job():
    return JobListing(
        title="Software Engineer",
        company="Acme Inc",
        url="https://example.com/job/1",
        location="San Francisco, CA",
        source="serpapi",
        match_score=0.75,
    )


class TestJobDatabase:
    def test_add_and_check_job(self, db, sample_job):
        assert not db.is_job_seen(sample_job.job_id)
        db.add_job(sample_job)
        assert db.is_job_seen(sample_job.job_id)

    def test_filter_new_jobs(self, db, sample_job):
        # First time: job is new
        new = db.filter_new_jobs([sample_job])
        assert len(new) == 1

        # Add it to DB
        db.add_job(sample_job)

        # Second time: job is seen
        new = db.filter_new_jobs([sample_job])
        assert len(new) == 0

    def test_mark_jobs_sent(self, db, sample_job):
        db.add_job(sample_job)
        db.mark_jobs_sent([sample_job.job_id])

        stats = db.get_stats()
        assert stats["total_jobs_sent"] == 1

    def test_record_run(self, db):
        db.record_run(jobs_fetched=100, new_jobs_found=10, jobs_matched=5, email_sent=True)

        stats = db.get_stats()
        assert stats["total_runs"] == 1
        assert stats["last_run"]["jobs_fetched"] == 100
        assert stats["last_run"]["email_sent"] is True

    def test_record_failed_run(self, db):
        db.record_run(error_message="Connection timeout")

        stats = db.get_stats()
        assert stats["last_run"]["error_message"] == "Connection timeout"

    def test_stats_empty_db(self, db):
        stats = db.get_stats()
        assert stats["total_jobs_tracked"] == 0
        assert stats["total_runs"] == 0

    def test_dedup_multiple_jobs(self, db):
        jobs = [
            JobListing(title="Job A", company="Co A", url="https://a.com"),
            JobListing(title="Job B", company="Co B", url="https://b.com"),
            JobListing(title="Job C", company="Co C", url="https://c.com"),
        ]

        # All new first time
        new = db.filter_new_jobs(jobs)
        assert len(new) == 3

        for job in jobs:
            db.add_job(job)

        # Add one more new job alongside existing ones
        jobs.append(JobListing(title="Job D", company="Co D", url="https://d.com"))
        new = db.filter_new_jobs(jobs)
        assert len(new) == 1
        assert new[0].title == "Job D"
