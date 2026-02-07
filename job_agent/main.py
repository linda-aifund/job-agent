"""Orchestrator - CLI entry point for the job agent pipeline."""

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path

from job_agent.config import load_config, validate_config, AppConfig
from job_agent.jobs.models import JobListing
from job_agent.matching.matcher import score_and_filter_jobs
from job_agent.notifications.email_sender import send_email
from job_agent.notifications.templates import render_job_email, render_test_email
from job_agent.profile.models import ProfileData
from job_agent.storage.database import JobDatabase
from job_agent.utils.logging_config import setup_logging

logger = logging.getLogger("job_agent")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Daily Job Agent - Automated job matching and notification",
    )
    parser.add_argument(
        "--config", default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--test-email", action="store_true",
        help="Send a test email and exit",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and match jobs but don't send email",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print database statistics and exit",
    )
    return parser.parse_args()


def load_profile(config: AppConfig) -> ProfileData:
    """Load candidate profile from configured source."""
    if config.profile.resume_path:
        from job_agent.profile.resume_parser import parse_resume
        logger.info("Parsing resume from: %s", config.profile.resume_path)
        return parse_resume(config.profile.resume_path)

    if config.profile.linkedin_url:
        from job_agent.profile.linkedin_scraper import scrape_linkedin_profile
        logger.info("Scraping LinkedIn profile: %s", config.profile.linkedin_url)
        return scrape_linkedin_profile(config.profile.linkedin_url)

    raise ValueError("No profile source configured. Set resume_path or linkedin_url in config.yaml")


def fetch_all_jobs(config: AppConfig) -> list[JobListing]:
    """Fetch jobs from all configured sources for all search titles."""
    all_jobs = []

    for title in config.search.job_titles:
        query = title
        location = config.search.location
        max_results = config.search.max_results_per_source

        # SerpAPI (primary)
        try:
            from job_agent.jobs.serpapi_source import fetch_serpapi_jobs
            jobs = fetch_serpapi_jobs(
                api_key=config.api_keys.serpapi_key,
                query=query,
                location=location,
                max_results=max_results,
            )
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error("SerpAPI source failed for '%s': %s", title, e)

        # Indeed (secondary)
        try:
            from job_agent.jobs.indeed_scraper import fetch_indeed_jobs
            jobs = fetch_indeed_jobs(
                query=query,
                location=location,
                max_results=max_results,
            )
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error("Indeed source failed for '%s': %s", title, e)

        # LinkedIn Jobs (secondary)
        try:
            from job_agent.jobs.linkedin_jobs import fetch_linkedin_jobs
            jobs = fetch_linkedin_jobs(
                query=query,
                location=location,
                max_results=max_results,
            )
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error("LinkedIn Jobs source failed for '%s': %s", title, e)

    logger.info("Total jobs fetched from all sources: %d", len(all_jobs))
    return all_jobs


def print_stats(db: JobDatabase):
    """Print database statistics."""
    stats = db.get_stats()
    print("\n=== Job Agent Statistics ===")
    print(f"Total jobs tracked: {stats['total_jobs_tracked']}")
    print(f"Jobs sent via email: {stats['total_jobs_sent']}")
    print(f"Unsent jobs: {stats['unsent_jobs']}")
    print(f"Total pipeline runs: {stats['total_runs']}")

    if stats.get("by_source"):
        print("\nJobs by source:")
        for source, count in stats["by_source"].items():
            print(f"  {source or 'unknown'}: {count}")

    if stats.get("last_run"):
        run = stats["last_run"]
        print(f"\nLast run: {run['run_at']}")
        print(f"  Fetched: {run['jobs_fetched']}")
        print(f"  New: {run['new_jobs_found']}")
        print(f"  Matched: {run['jobs_matched']}")
        print(f"  Email sent: {'Yes' if run['email_sent'] else 'No'}")
        if run["error_message"]:
            print(f"  Error: {run['error_message']}")
    print()


def run_pipeline(config: AppConfig, dry_run: bool = False):
    """Run the full job matching pipeline."""
    db_path = str(Path(config.data_dir) / "jobs.db")

    with JobDatabase(db_path) as db:
        try:
            # Step 1: Parse profile
            logger.info("Step 1: Loading candidate profile...")
            profile = load_profile(config)
            logger.info(
                "Profile loaded: %s (%d skills, %d keywords)",
                profile.name or "Unknown",
                len(profile.skills),
                len(profile.keywords),
            )

            # Step 2: Fetch jobs from all sources
            logger.info("Step 2: Fetching jobs from all sources...")
            all_jobs = fetch_all_jobs(config)
            jobs_fetched = len(all_jobs)

            if not all_jobs:
                logger.warning("No jobs fetched from any source")
                db.record_run(jobs_fetched=0, new_jobs_found=0, jobs_matched=0)
                return

            # Step 3: Deduplicate against database
            logger.info("Step 3: Deduplicating against database...")
            new_jobs = db.filter_new_jobs(all_jobs)
            logger.info("New jobs after dedup: %d/%d", len(new_jobs), len(all_jobs))

            if not new_jobs:
                logger.info("No new jobs found - all have been seen before")
                db.record_run(
                    jobs_fetched=jobs_fetched,
                    new_jobs_found=0,
                    jobs_matched=0,
                )
                return

            # Step 4: Score and filter
            logger.info("Step 4: Scoring and filtering jobs...")
            matched_jobs = score_and_filter_jobs(profile, new_jobs, config)
            logger.info("Jobs above threshold: %d", len(matched_jobs))

            # Add all new jobs to DB (even unmatched, for dedup tracking)
            for job in new_jobs:
                db.add_job(job)

            if not matched_jobs:
                logger.info("No jobs above match threshold")
                db.record_run(
                    jobs_fetched=jobs_fetched,
                    new_jobs_found=len(new_jobs),
                    jobs_matched=0,
                )
                return

            # Step 5: Send email
            email_sent = False
            if dry_run:
                logger.info("DRY RUN - Skipping email. Would send %d jobs:", len(matched_jobs))
                for i, job in enumerate(matched_jobs[:10], 1):
                    logger.info(
                        "  #%d [%.0f%%] %s @ %s",
                        i, job.match_score * 100, job.title, job.company,
                    )
            else:
                logger.info("Step 5: Sending email with %d matched jobs...", len(matched_jobs))
                subject, html = render_job_email(matched_jobs)
                email_sent = send_email(config.email, subject, html)

                if email_sent:
                    db.mark_jobs_sent([j.job_id for j in matched_jobs])
                    logger.info("Email sent and jobs marked in database")
                else:
                    logger.error("Failed to send email - jobs will be retried next run")

            db.record_run(
                jobs_fetched=jobs_fetched,
                new_jobs_found=len(new_jobs),
                jobs_matched=len(matched_jobs),
                email_sent=email_sent,
            )

            logger.info("Pipeline complete: %d fetched, %d new, %d matched",
                        jobs_fetched, len(new_jobs), len(matched_jobs))

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error("Pipeline failed: %s\n%s", error_msg, traceback.format_exc())
            db.record_run(error_message=error_msg)
            raise


def main():
    args = parse_args()

    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    setup_logging(config.log_dir)

    # Validate config and print warnings
    warnings = validate_config(config)
    for w in warnings:
        logger.warning("Config: %s", w)

    # Handle --stats
    if args.stats:
        db_path = str(Path(config.data_dir) / "jobs.db")
        with JobDatabase(db_path) as db:
            print_stats(db)
        return

    # Handle --test-email
    if args.test_email:
        logger.info("Sending test email...")
        subject, html = render_test_email()
        success = send_email(config.email, subject, html)
        if success:
            print("Test email sent successfully!")
        else:
            print("Failed to send test email. Check logs for details.", file=sys.stderr)
            sys.exit(1)
        return

    # Run the main pipeline
    try:
        run_pipeline(config, dry_run=args.dry_run)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
