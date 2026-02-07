"""Tests for configuration loading."""

import os
import tempfile

import pytest
import yaml

from job_agent.config import AppConfig, load_config, validate_config


@pytest.fixture
def config_file():
    """Create a temporary config file."""
    config_data = {
        "profile": {"resume_path": "/path/to/resume.pdf"},
        "search": {
            "job_titles": ["Software Engineer"],
            "location": "Silicon Valley, CA",
        },
        "api_keys": {"serpapi_key": "test_key"},
        "email": {
            "sender_email": "test@gmail.com",
            "sender_password": "app_password",
            "recipient_email": "recipient@gmail.com",
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        path = f.name

    yield path
    os.unlink(path)


class TestLoadConfig:
    def test_loads_valid_config(self, config_file):
        config = load_config(config_file)
        assert config.profile.resume_path == "/path/to/resume.pdf"
        assert config.search.job_titles == ["Software Engineer"]
        assert config.api_keys.serpapi_key == "test_key"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")

    def test_defaults_applied(self):
        config_data = {"profile": {"resume_path": "resume.pdf"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            path = f.name

        try:
            config = load_config(path)
            assert config.search.location == "Silicon Valley, CA"
            assert config.matching.score_threshold == 0.3
            assert config.email.smtp_server == "smtp.gmail.com"
        finally:
            os.unlink(path)


class TestValidateConfig:
    def test_no_profile_source_warns(self):
        config = AppConfig()
        warnings = validate_config(config)
        assert any("profile source" in w.lower() for w in warnings)

    def test_no_serpapi_warns(self):
        config = AppConfig()
        config.profile.resume_path = "resume.pdf"
        warnings = validate_config(config)
        assert any("serpapi" in w.lower() for w in warnings)

    def test_ai_without_key_warns(self):
        config = AppConfig()
        config.profile.resume_path = "resume.pdf"
        config.matching.use_ai_matching = True
        warnings = validate_config(config)
        assert any("openai" in w.lower() for w in warnings)

    def test_valid_config_no_critical_warnings(self, config_file):
        config = load_config(config_file)
        warnings = validate_config(config)
        # Should not have profile or email warnings
        assert not any("profile source" in w.lower() for w in warnings)
        assert not any("email credentials" in w.lower() for w in warnings)
