# Job Agent

[![CI](https://github.com/linda-aifund/job-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/linda-aifund/job-agent/actions/workflows/ci.yml)

A Python-based daily job agent that automatically finds, matches, and emails you relevant job listings every morning.

## How It Works

1. **Parses your profile** from a resume (PDF/TXT) or LinkedIn URL
2. **Fetches jobs** from multiple sources (Google Jobs via SerpAPI, Indeed, LinkedIn)
3. **Scores matches** using keyword overlap (with optional OpenAI semantic matching)
4. **Deduplicates** against a local SQLite database so you only see new listings
5. **Emails you** a styled HTML digest of matching jobs via Gmail SMTP
6. **Runs daily** via Windows Task Scheduler

## Quick Start

### 1. Install

```bash
git clone https://github.com/linda-aifund/job-agent.git
cd job-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
copy config.example.yaml config.yaml
```

Edit `config.yaml` with your settings:

- **Profile source** — path to your resume or LinkedIn URL
- **Search preferences** — job titles, location, experience level
- **API keys** — SerpAPI key (required for Google Jobs), OpenAI key (optional)
- **Email** — Gmail address and [App Password](https://myaccount.google.com/apppasswords)

API keys can also be set via environment variables: `SERPAPI_KEY`, `OPENAI_API_KEY`, `JOB_AGENT_EMAIL_PASSWORD`.

### 3. Run

```bash
# Verify email config
python -m job_agent.main --test-email

# Fetch and match without sending email
python -m job_agent.main --dry-run

# Full pipeline
python -m job_agent.main
```

### 4. Schedule (Optional)

Run `setup_task.bat` as Administrator to create a Windows Scheduled Task that runs the agent daily at 8:00 AM.

## CLI Options

| Flag | Description |
|------|-------------|
| `--config PATH` | Custom config file path (default: `config.yaml`) |
| `--test-email` | Send a test email and exit |
| `--dry-run` | Fetch and match jobs but don't send email |
| `--stats` | Print database statistics and exit |

## Matching Algorithm

**Keyword matcher** (default, free):

| Component | Weight | Method |
|-----------|--------|--------|
| Skills overlap | 40% | Recognized tech skills in common |
| Title similarity | 30% | Normalized job title word overlap |
| Keyword overlap | 20% | Frequency-based keyword matching |
| Experience alignment | 10% | Years of experience comparison |

**AI matcher** (optional, requires OpenAI API key): Sends profile + job description to `gpt-4o-mini` for semantic scoring. Only scores jobs that pass a keyword pre-filter (default >0.2) to limit API costs.

## Project Structure

```
job-agent/
├── config.yaml              # Your configuration (git-ignored)
├── config.example.yaml      # Template with all options documented
├── requirements.txt
├── run.bat                  # Venv activation + script runner
├── setup_task.bat           # Creates Windows Scheduled Task
│
├── job_agent/
│   ├── main.py              # CLI entry point and orchestrator
│   ├── config.py            # YAML config loading + validation
│   ├── profile/             # Resume and LinkedIn parsing
│   ├── jobs/                # Job fetching from multiple sources
│   ├── matching/            # Keyword and AI scoring
│   ├── storage/             # SQLite deduplication and run history
│   ├── notifications/       # HTML email templates and SMTP sender
│   └── utils/               # HTTP client, text processing, logging
│
├── data/                    # SQLite database (created at runtime)
├── logs/                    # Log files (created at runtime)
└── tests/                   # Unit tests
```

## Tests

```bash
pytest tests/ -v
```

## Requirements

- Python 3.10+
- A [SerpAPI](https://serpapi.com/) key for Google Jobs search
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) for sending notifications
- (Optional) An [OpenAI API](https://platform.openai.com/) key for AI-powered matching
