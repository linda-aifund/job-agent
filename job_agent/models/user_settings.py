"""User settings model — search, matching, email, API keys, schedule."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Search config
    job_titles: Mapped[list] = mapped_column(JSON, default=lambda: ["Software Engineer"])
    location: Mapped[str] = mapped_column(String(255), default="")
    remote_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    max_results_per_source: Mapped[int] = mapped_column(Integer, default=50)

    # Matching config
    score_threshold: Mapped[float] = mapped_column(Float, default=0.3)
    use_ai_matching: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_pre_filter_threshold: Mapped[float] = mapped_column(Float, default=0.2)

    # API keys
    serpapi_key: Mapped[str] = mapped_column(String(255), default="")
    openai_api_key: Mapped[str] = mapped_column(String(255), default="")

    # Email config
    smtp_server: Mapped[str] = mapped_column(String(255), default="smtp.gmail.com")
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)
    sender_email: Mapped[str] = mapped_column(String(255), default="")
    sender_password: Mapped[str] = mapped_column(String(255), default="")
    recipient_email: Mapped[str] = mapped_column(String(255), default="")
    resend_api_key: Mapped[str] = mapped_column(String(255), default="")

    # Schedule config
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_frequency: Mapped[str] = mapped_column(String(20), default="weekly")  # daily, weekly, monthly
    schedule_day_of_week: Mapped[str] = mapped_column(String(10), default="mon")  # mon, tue, ...
    schedule_day_of_month: Mapped[int] = mapped_column(Integer, default=1)
    schedule_hour: Mapped[int] = mapped_column(Integer, default=9)
    schedule_minute: Mapped[int] = mapped_column(Integer, default=0)
    schedule_timezone: Mapped[str] = mapped_column(String(50), default="America/New_York")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="settings")
