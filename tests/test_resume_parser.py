"""Tests for resume parser."""

import os
import tempfile

import pytest

from job_agent.profile.resume_parser import parse_resume


@pytest.fixture
def sample_resume_txt():
    """Create a sample text resume file."""
    content = """John Smith
john.smith@email.com
(555) 123-4567

Summary:
Experienced Software Engineer with 7 years of experience building scalable
backend systems using Python, Java, and cloud technologies.

Experience:
Senior Software Engineer at Google
- Built microservices using Python and Kubernetes
- Managed AWS infrastructure with Terraform
- Led team of 5 engineers

Software Engineer at Meta
- Developed backend APIs with Java and Spring
- Implemented CI/CD pipelines with Jenkins
- Worked with PostgreSQL and Redis

Skills:
Python, Java, Docker, Kubernetes, AWS, Terraform, PostgreSQL, Redis, Git

Education:
BS Computer Science, Stanford University
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name

    yield path
    os.unlink(path)


class TestResumeParser:
    def test_parse_text_resume(self, sample_resume_txt):
        profile = parse_resume(sample_resume_txt)
        assert profile.email == "john.smith@email.com"
        assert profile.phone == "(555) 123-4567"
        assert "python" in profile.skills
        assert "java" in profile.skills
        assert "docker" in profile.skills
        assert profile.experience_years == 7
        assert len(profile.keywords) > 0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_resume("/nonexistent/resume.pdf")

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            with pytest.raises(ValueError, match="Unsupported"):
                parse_resume(path)
        finally:
            os.unlink(path)

    def test_empty_file_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            path = f.name
        try:
            with pytest.raises(ValueError, match="empty"):
                parse_resume(path)
        finally:
            os.unlink(path)

    def test_skills_extraction(self, sample_resume_txt):
        profile = parse_resume(sample_resume_txt)
        expected_skills = {"python", "java", "docker", "kubernetes", "aws", "terraform", "postgresql", "redis", "git"}
        assert profile.skills & expected_skills == expected_skills

    def test_name_extraction(self, sample_resume_txt):
        profile = parse_resume(sample_resume_txt)
        assert profile.name == "John Smith"
