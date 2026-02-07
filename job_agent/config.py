"""YAML config loading and validation."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class EmailConfig:
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""  # Gmail App Password
    recipient_email: str = ""


@dataclass
class SearchConfig:
    job_titles: list[str] = field(default_factory=lambda: ["Software Engineer"])
    location: str = "Silicon Valley, CA"
    remote_ok: bool = True
    experience_years: int = 0
    max_results_per_source: int = 50


@dataclass
class MatchingConfig:
    score_threshold: float = 0.3
    use_ai_matching: bool = False
    ai_pre_filter_threshold: float = 0.2


@dataclass
class ApiKeys:
    serpapi_key: str = ""
    openai_api_key: str = ""


@dataclass
class ProfileConfig:
    resume_path: str = ""
    linkedin_url: str = ""


@dataclass
class AppConfig:
    email: EmailConfig = field(default_factory=EmailConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    api_keys: ApiKeys = field(default_factory=ApiKeys)
    profile: ProfileConfig = field(default_factory=ProfileConfig)
    data_dir: str = "data"
    log_dir: str = "logs"


def load_config(config_path: str = "config.yaml") -> AppConfig:
    """Load and validate configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            "Copy config.example.yaml to config.yaml and fill in your settings."
        )

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    config = AppConfig()

    # Email
    email_raw = raw.get("email", {})
    config.email = EmailConfig(
        smtp_server=email_raw.get("smtp_server", "smtp.gmail.com"),
        smtp_port=email_raw.get("smtp_port", 587),
        sender_email=email_raw.get("sender_email", ""),
        sender_password=os.environ.get("JOB_AGENT_EMAIL_PASSWORD", email_raw.get("sender_password", "")),
        recipient_email=email_raw.get("recipient_email", ""),
    )

    # Search
    search_raw = raw.get("search", {})
    config.search = SearchConfig(
        job_titles=search_raw.get("job_titles", ["Software Engineer"]),
        location=search_raw.get("location", "Silicon Valley, CA"),
        remote_ok=search_raw.get("remote_ok", True),
        experience_years=search_raw.get("experience_years", 0),
        max_results_per_source=search_raw.get("max_results_per_source", 50),
    )

    # Matching
    matching_raw = raw.get("matching", {})
    config.matching = MatchingConfig(
        score_threshold=matching_raw.get("score_threshold", 0.3),
        use_ai_matching=matching_raw.get("use_ai_matching", False),
        ai_pre_filter_threshold=matching_raw.get("ai_pre_filter_threshold", 0.2),
    )

    # API keys (env vars take precedence)
    keys_raw = raw.get("api_keys", {})
    config.api_keys = ApiKeys(
        serpapi_key=os.environ.get("SERPAPI_KEY", keys_raw.get("serpapi_key", "")),
        openai_api_key=os.environ.get("OPENAI_API_KEY", keys_raw.get("openai_api_key", "")),
    )

    # Profile
    profile_raw = raw.get("profile", {})
    config.profile = ProfileConfig(
        resume_path=profile_raw.get("resume_path", ""),
        linkedin_url=profile_raw.get("linkedin_url", ""),
    )

    config.data_dir = raw.get("data_dir", "data")
    config.log_dir = raw.get("log_dir", "logs")

    return config


def validate_config(config: AppConfig) -> list[str]:
    """Return list of validation warnings (empty = OK)."""
    warnings = []

    if not config.profile.resume_path and not config.profile.linkedin_url:
        warnings.append("No profile source configured (resume_path or linkedin_url required)")

    if not config.api_keys.serpapi_key:
        warnings.append("No SerpAPI key configured - primary job source will be unavailable")

    if not config.email.sender_email or not config.email.sender_password:
        warnings.append("Email credentials not configured - notifications will fail")

    if not config.email.recipient_email:
        warnings.append("No recipient email configured")

    if config.matching.use_ai_matching and not config.api_keys.openai_api_key:
        warnings.append("AI matching enabled but no OpenAI API key configured - will fall back to keyword matching")

    return warnings
