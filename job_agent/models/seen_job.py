"""Seen job model — per-user job deduplication and history."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class SeenJob(Base):
    __tablename__ = "seen_jobs_v2"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256 hex

    title: Mapped[str] = mapped_column(String(500), default="")
    company: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(String(2048), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    salary: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(50), default="")
    posted_date: Mapped[str] = mapped_column(String(50), default="")
    job_type: Mapped[str] = mapped_column(String(50), default="")
    remote: Mapped[bool] = mapped_column(Boolean, default=False)

    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    match_reason: Mapped[str] = mapped_column(Text, default="")

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="seen_jobs")
