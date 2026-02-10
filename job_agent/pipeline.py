"""Pipeline adapter — converts DB config into AppConfig and runs the existing pipeline."""

import logging
import smtplib
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from job_agent.config import AppConfig, EmailConfig, SearchConfig, MatchingConfig, ApiKeys, ProfileConfig
from job_agent.jobs.models import JobListing
from job_agent.main import fetch_all_jobs
from job_agent.matching.matcher import score_and_filter_jobs
from job_agent.models import SessionLocal, SeenJob, RunHistory, UserProfile, UserSettings
from job_agent.notifications.templates import render_job_email

logger = logging.getLogger("job_agent.pipeline")


def _send_email_with_detail(
    config: EmailConfig, subject: str, html_body: str, resend_api_key: str = ""
) -> bool:
    """Send email via Resend (HTTP) if key provided, otherwise SMTP. Raises on failure."""
    if resend_api_key:
        import resend
        resend.api_key = resend_api_key
        resend.Emails.send({
            "from": f"Job Agent <{config.sender_email}>",
            "to": [config.recipient_email],
            "subject": subject,
            "html": html_body,
        })
        return True

    # Fallback to SMTP (won't work on Railway / most cloud hosts)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.sender_email
    msg["To"] = config.recipient_email
    msg.attach(MIMEText(f"View this email in an HTML-capable client.\n\nSubject: {subject}", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(config.smtp_server, config.smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(config.sender_email, config.sender_password)
        server.sendmail(config.sender_email, config.recipient_email, msg.as_string())

    return True


def _no_matches_email(jobs_fetched: int, new_jobs: int) -> str:
    """Render a simple HTML email for runs with no new matches."""
    return f"""\
<html><body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #333;">Job Agent — No New Matches</h2>
<p>Your scheduled pipeline ran successfully but found no new matches this time.</p>
<table style="border-collapse: collapse; margin: 16px 0;">
<tr><td style="padding: 4px 12px; color: #666;">Jobs scanned</td><td style="padding: 4px 12px;"><strong>{jobs_fetched}</strong></td></tr>
<tr><td style="padding: 4px 12px; color: #666;">New (unseen) jobs</td><td style="padding: 4px 12px;"><strong>{new_jobs}</strong></td></tr>
<tr><td style="padding: 4px 12px; color: #666;">Matches above threshold</td><td style="padding: 4px 12px;"><strong>0</strong></td></tr>
</table>
<p style="color: #888; font-size: 13px;">This email confirms the scheduler is working. You'll receive matches when new relevant jobs appear.</p>
</body></html>"""


def build_app_config_for_user(settings: UserSettings, profile: UserProfile) -> AppConfig:
    """Construct an AppConfig dataclass from database rows."""
    return AppConfig(
        email=EmailConfig(
            smtp_server=settings.smtp_server or "smtp.gmail.com",
            smtp_port=settings.smtp_port or 587,
            sender_email=settings.sender_email or "",
            sender_password=settings.sender_password or "",
            recipient_email=settings.recipient_email or "",
        ),
        search=SearchConfig(
            job_titles=settings.job_titles or ["Software Engineer"],
            location=settings.location or "",
            remote_ok=settings.remote_ok,
            experience_years=settings.experience_years or 0,
            max_results_per_source=settings.max_results_per_source or 50,
        ),
        matching=MatchingConfig(
            score_threshold=settings.score_threshold or 0.3,
            use_ai_matching=settings.use_ai_matching,
            ai_pre_filter_threshold=settings.ai_pre_filter_threshold or 0.2,
        ),
        api_keys=ApiKeys(
            serpapi_key=settings.serpapi_key or "",
            openai_api_key=settings.openai_api_key or "",
        ),
        profile=ProfileConfig(),  # Not used — we build ProfileData from DB directly
    )


def run_pipeline_for_user(user_id: int) -> None:
    """Full pipeline run for a single user. Safe to call from a thread or scheduler."""
    db = SessionLocal()
    start = time.time()
    try:
        profile_row = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not profile_row or not settings:
            logger.error("User %d missing profile or settings — skipping", user_id)
            return

        config = build_app_config_for_user(settings, profile_row)
        profile_data = profile_row.to_profile_data()

        # Augment profile with search titles (mirrors CLI behaviour in main.load_profile)
        for title in config.search.job_titles:
            if title not in profile_data.job_titles:
                profile_data.job_titles.append(title)

        # Step 1: Fetch jobs
        logger.info("[user:%d] Fetching jobs...", user_id)
        all_jobs = fetch_all_jobs(config)
        jobs_fetched = len(all_jobs)

        new_jobs = []
        matched_jobs = []
        now = datetime.now(timezone.utc)

        if not all_jobs:
            logger.info("[user:%d] No jobs fetched", user_id)
        else:
            # Step 2: Deduplicate against user's seen_jobs_v2
            seen_ids = {
                row.job_id
                for row in db.query(SeenJob.job_id).filter(SeenJob.user_id == user_id).all()
            }
            new_jobs = [j for j in all_jobs if j.job_id not in seen_ids]
            logger.info("[user:%d] New jobs after dedup: %d/%d", user_id, len(new_jobs), jobs_fetched)

            if new_jobs:
                # Step 3: Score and filter
                matched_jobs = score_and_filter_jobs(profile_data, new_jobs, config)
                logger.info("[user:%d] Jobs above threshold: %d", user_id, len(matched_jobs))

                # Persist all new jobs (even unmatched, for dedup)
                for job in new_jobs:
                    db.add(SeenJob(
                        user_id=user_id,
                        job_id=job.job_id,
                        title=job.title,
                        company=job.company,
                        url=job.url,
                        location=job.location,
                        description=job.description[:2000] if job.description else "",
                        salary=job.salary,
                        source=job.source,
                        posted_date=job.posted_date,
                        job_type=job.job_type,
                        remote=job.remote,
                        match_score=job.match_score,
                        match_reason=job.match_reason,
                        first_seen_at=now,
                        last_seen_at=now,
                    ))
                db.flush()

                # Deduplicate by (title, company)
                seen_pairs: set[tuple[str, str]] = set()
                unique_matched: list[JobListing] = []
                for job in matched_jobs:
                    key = (job.title.strip().lower(), job.company.strip().lower())
                    if key not in seen_pairs:
                        seen_pairs.add(key)
                        unique_matched.append(job)
                matched_jobs = unique_matched

        # Step 4: Send email (always — with matches or a summary)
        email_sent = False
        email_error = None
        resend_key = settings.resend_api_key if hasattr(settings, "resend_api_key") else ""
        if not config.email.sender_email:
            email_error = "Sender email not configured"
            logger.warning("[user:%d] %s", user_id, email_error)
        elif not resend_key and not config.email.sender_password:
            email_error = "Sender password not configured (or add a Resend API key)"
            logger.warning("[user:%d] %s", user_id, email_error)
        elif not config.email.recipient_email:
            email_error = "Recipient email not configured"
            logger.warning("[user:%d] %s", user_id, email_error)
        else:
            if matched_jobs:
                subject, html = render_job_email(matched_jobs)
            else:
                subject = "Job Agent — No New Matches"
                html = _no_matches_email(jobs_fetched, len(new_jobs))
            try:
                email_sent = _send_email_with_detail(config.email, subject, html, resend_key)
            except Exception as smtp_exc:
                email_sent = False
                email_error = f"Email error: {type(smtp_exc).__name__}: {smtp_exc}"
                logger.error("[user:%d] %s", user_id, email_error)
            if email_sent:
                matched_ids = {j.job_id for j in matched_jobs}
                db.query(SeenJob).filter(
                    SeenJob.user_id == user_id,
                    SeenJob.job_id.in_(matched_ids),
                ).update({SeenJob.sent_at: now}, synchronize_session=False)

        _record_run(
            db, user_id, start,
            jobs_fetched=jobs_fetched,
            new_jobs_found=len(new_jobs),
            jobs_matched=len(matched_jobs),
            email_sent=email_sent,
            error_message=email_error,
        )
        db.commit()
        logger.info(
            "[user:%d] Pipeline done: %d fetched, %d new, %d matched, email=%s",
            user_id, jobs_fetched, len(new_jobs), len(matched_jobs), email_sent,
        )

    except Exception as e:
        logger.error("[user:%d] Pipeline failed: %s", user_id, e, exc_info=True)
        try:
            _record_run(db, user_id, start, error_message=str(e))
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def _record_run(
    db,
    user_id: int,
    start: float,
    jobs_fetched: int = 0,
    new_jobs_found: int = 0,
    jobs_matched: int = 0,
    email_sent: bool = False,
    error_message: str | None = None,
):
    db.add(RunHistory(
        user_id=user_id,
        jobs_fetched=jobs_fetched,
        new_jobs_found=new_jobs_found,
        jobs_matched=jobs_matched,
        email_sent=email_sent,
        error_message=error_message,
        duration_seconds=round(time.time() - start, 2),
    ))
