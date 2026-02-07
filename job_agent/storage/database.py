"""SQLite storage for job deduplication and run history."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from job_agent.jobs.models import JobListing

logger = logging.getLogger("job_agent.storage")


class JobDatabase:
    """SQLite database for tracking seen jobs and run history."""

    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._create_tables()

    def _connect(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                url TEXT NOT NULL,
                location TEXT DEFAULT '',
                source TEXT DEFAULT '',
                match_score REAL DEFAULT 0.0,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                sent_at TEXT DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS run_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT NOT NULL,
                jobs_fetched INTEGER DEFAULT 0,
                new_jobs_found INTEGER DEFAULT 0,
                jobs_matched INTEGER DEFAULT 0,
                email_sent INTEGER DEFAULT 0,
                error_message TEXT DEFAULT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_seen_jobs_sent
                ON seen_jobs(sent_at);
            CREATE INDEX IF NOT EXISTS idx_seen_jobs_source
                ON seen_jobs(source);
        """)
        self.conn.commit()

    def is_job_seen(self, job_id: str) -> bool:
        """Check if a job has been seen before."""
        cursor = self.conn.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)
        )
        return cursor.fetchone() is not None

    def filter_new_jobs(self, jobs: list[JobListing]) -> list[JobListing]:
        """Return only jobs not previously seen. Updates last_seen_at for known jobs."""
        new_jobs = []
        now = datetime.now().isoformat()

        for job in jobs:
            if self.is_job_seen(job.job_id):
                self.conn.execute(
                    "UPDATE seen_jobs SET last_seen_at = ? WHERE job_id = ?",
                    (now, job.job_id),
                )
            else:
                new_jobs.append(job)

        self.conn.commit()
        return new_jobs

    def add_job(self, job: JobListing):
        """Insert a new job into the database."""
        now = datetime.now().isoformat()
        self.conn.execute(
            """INSERT OR IGNORE INTO seen_jobs
               (job_id, title, company, url, location, source, match_score, first_seen_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job.job_id, job.title, job.company, job.url,
                job.location, job.source, job.match_score, now, now,
            ),
        )
        self.conn.commit()

    def mark_jobs_sent(self, job_ids: list[str]):
        """Mark jobs as sent via email."""
        now = datetime.now().isoformat()
        for jid in job_ids:
            self.conn.execute(
                "UPDATE seen_jobs SET sent_at = ? WHERE job_id = ?",
                (now, jid),
            )
        self.conn.commit()

    def record_run(
        self,
        jobs_fetched: int = 0,
        new_jobs_found: int = 0,
        jobs_matched: int = 0,
        email_sent: bool = False,
        error_message: Optional[str] = None,
    ):
        """Record a pipeline run in history."""
        self.conn.execute(
            """INSERT INTO run_history
               (run_at, jobs_fetched, new_jobs_found, jobs_matched, email_sent, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                jobs_fetched,
                new_jobs_found,
                jobs_matched,
                1 if email_sent else 0,
                error_message,
            ),
        )
        self.conn.commit()

    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {}

        row = self.conn.execute("SELECT COUNT(*) as cnt FROM seen_jobs").fetchone()
        stats["total_jobs_tracked"] = row["cnt"]

        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM seen_jobs WHERE sent_at IS NOT NULL"
        ).fetchone()
        stats["total_jobs_sent"] = row["cnt"]

        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM seen_jobs WHERE sent_at IS NULL"
        ).fetchone()
        stats["unsent_jobs"] = row["cnt"]

        row = self.conn.execute("SELECT COUNT(*) as cnt FROM run_history").fetchone()
        stats["total_runs"] = row["cnt"]

        row = self.conn.execute(
            "SELECT * FROM run_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            stats["last_run"] = {
                "run_at": row["run_at"],
                "jobs_fetched": row["jobs_fetched"],
                "new_jobs_found": row["new_jobs_found"],
                "jobs_matched": row["jobs_matched"],
                "email_sent": bool(row["email_sent"]),
                "error_message": row["error_message"],
            }

        # Source breakdown
        rows = self.conn.execute(
            "SELECT source, COUNT(*) as cnt FROM seen_jobs GROUP BY source"
        ).fetchall()
        stats["by_source"] = {row["source"]: row["cnt"] for row in rows}

        return stats

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
