"""Tests for text processing utilities."""

from job_agent.utils.text_processing import (
    extract_keywords,
    extract_skills,
    extract_years_experience,
    is_silicon_valley_location,
    normalize_title,
    title_similarity,
)


class TestExtractSkills:
    def test_basic_skills(self):
        text = "Experience with Python, Java, and Docker in a cloud environment"
        skills = extract_skills(text)
        assert "python" in skills
        assert "java" in skills
        assert "docker" in skills

    def test_case_insensitive(self):
        text = "Worked with KUBERNETES and React.js"
        skills = extract_skills(text)
        assert "kubernetes" in skills
        assert "react" in skills

    def test_no_false_positives_for_short_skills(self):
        text = "Are you ready to go?"
        skills = extract_skills(text)
        assert "r" not in skills  # "r" should not match inside "are" or "ready"

    def test_go_language(self):
        text = "Proficient in Go and Rust programming"
        skills = extract_skills(text)
        assert "go" in skills
        assert "rust" in skills

    def test_empty_text(self):
        assert extract_skills("") == set()


class TestExtractKeywords:
    def test_extracts_meaningful_words(self):
        text = "Python developer with machine learning experience using tensorflow"
        keywords = extract_keywords(text, top_n=10)
        assert "python" in keywords
        assert "tensorflow" in keywords

    def test_excludes_stop_words(self):
        text = "The quick brown fox jumps over the lazy dog"
        keywords = extract_keywords(text)
        assert "the" not in keywords

    def test_empty_text(self):
        assert extract_keywords("") == []


class TestTitleSimilarity:
    def test_exact_match(self):
        assert title_similarity("Software Engineer", "Software Engineer") == 1.0

    def test_seniority_ignored(self):
        assert title_similarity("Senior Software Engineer", "Software Engineer") == 1.0

    def test_partial_match(self):
        score = title_similarity("Software Engineer", "Software Developer")
        assert 0.0 < score < 1.0

    def test_no_match(self):
        score = title_similarity("Software Engineer", "Product Manager")
        assert score == 0.0


class TestNormalizeTitle:
    def test_strips_seniority(self):
        assert normalize_title("Senior Software Engineer") == "software engineer"
        assert normalize_title("Jr. Software Engineer") == "software engineer"
        assert normalize_title("Lead Software Engineer") == "software engineer"

    def test_strips_levels(self):
        assert normalize_title("Software Engineer III") == "software engineer"

    def test_basic_normalization(self):
        assert normalize_title("  Software Engineer  ") == "software engineer"


class TestExtractYearsExperience:
    def test_basic_pattern(self):
        assert extract_years_experience("5+ years of experience") == 5

    def test_years_exp(self):
        assert extract_years_experience("3 years experience required") == 3

    def test_no_experience(self):
        assert extract_years_experience("Great opportunity for growth") is None

    def test_yrs_abbreviation(self):
        assert extract_years_experience("7+ yrs exp") == 7


class TestIsSiliconValleyLocation:
    def test_san_francisco(self):
        assert is_silicon_valley_location("San Francisco, CA")

    def test_mountain_view(self):
        assert is_silicon_valley_location("Mountain View, California")

    def test_bay_area(self):
        assert is_silicon_valley_location("Bay Area")

    def test_non_sv(self):
        assert not is_silicon_valley_location("New York, NY")

    def test_case_insensitive(self):
        assert is_silicon_valley_location("SILICON VALLEY")
