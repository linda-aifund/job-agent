"""APScheduler setup — manages per-user pipeline schedules."""

import logging
import traceback

from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("job_agent.scheduler")

_scheduler: BackgroundScheduler | None = None


def _job_listener(event):
    """Log scheduler job events for debugging."""
    if event.exception:
        logger.error("Scheduled job %s FAILED: %s", event.job_id, event.exception)
        logger.error("Traceback: %s", event.traceback)
    elif hasattr(event, "job_id"):
        if event.code == EVENT_JOB_MISSED:
            logger.warning("Scheduled job %s MISSED its fire time", event.job_id)
        else:
            logger.info("Scheduled job %s executed successfully", event.job_id)


def init_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    _scheduler.start()
    logger.info("APScheduler started")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler stopped")


def _job_id(user_id: int) -> str:
    return f"pipeline_user_{user_id}"


def _run_pipeline_wrapper(user_id: int) -> None:
    """Wrapper for scheduled execution — adds entry/exit logging."""
    logger.info("=== SCHEDULER FIRING pipeline for user %d ===", user_id)
    try:
        from job_agent.pipeline import run_pipeline_for_user
        run_pipeline_for_user(user_id)
        logger.info("=== SCHEDULER COMPLETED pipeline for user %d ===", user_id)
    except Exception:
        logger.error("=== SCHEDULER FAILED pipeline for user %d ===\n%s", user_id, traceback.format_exc())
        raise


def schedule_user_pipeline(user_id: int, settings) -> None:
    """Add, update, or remove a user's scheduled pipeline job."""
    global _scheduler
    if _scheduler is None:
        init_scheduler()

    job_id = _job_id(user_id)

    # Remove existing job if any
    existing = _scheduler.get_job(job_id)
    if existing:
        _scheduler.remove_job(job_id)
        logger.info("Removed existing schedule for user %d", user_id)

    if not settings.schedule_enabled:
        return

    # Build cron trigger from user settings
    freq = settings.schedule_frequency or "weekly"
    kwargs: dict = {
        "hour": settings.schedule_hour or 9,
        "minute": settings.schedule_minute or 0,
        "timezone": settings.schedule_timezone or "America/New_York",
    }

    if freq == "daily":
        pass  # Runs every day at the specified hour:minute
    elif freq == "weekly":
        kwargs["day_of_week"] = settings.schedule_day_of_week or "mon"
    elif freq == "monthly":
        kwargs["day"] = settings.schedule_day_of_month or 1

    trigger = CronTrigger(**kwargs)

    _scheduler.add_job(
        _run_pipeline_wrapper,
        trigger=trigger,
        args=[user_id],
        id=job_id,
        name=f"Pipeline for user {user_id}",
        misfire_grace_time=3600,
        coalesce=True,
        replace_existing=True,
    )
    logger.info("Scheduled pipeline for user %d: %s at %s", user_id, freq, trigger)


def get_next_run_time(user_id: int):
    """Return the next scheduled fire time for a user, or None."""
    global _scheduler
    if _scheduler is None:
        return None
    job = _scheduler.get_job(_job_id(user_id))
    if job:
        return job.next_run_time
    return None


def get_scheduler_info() -> dict:
    """Return diagnostic info about the scheduler state."""
    global _scheduler
    if _scheduler is None:
        return {"running": False, "jobs": []}
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return {
        "running": _scheduler.running,
        "jobs": jobs,
    }
