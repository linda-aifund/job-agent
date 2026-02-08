"""User profile model — stores parsed resume/LinkedIn data."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from job_agent.profile.models import ProfileData

from .base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    resume_filename: Mapped[str] = mapped_column(String(255), default="")
    resume_path: Mapped[str] = mapped_column(String(512), default="")
    linkedin_url: Mapped[str] = mapped_column(String(512), default="")

    name: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    job_titles: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    education: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    raw_text: Mapped[str] = mapped_column(Text, default="")

    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="profile")

    def to_profile_data(self) -> ProfileData:
        """Convert DB row to the existing ProfileData dataclass."""
        return ProfileData(
            name=self.name or "",
            phone=self.phone or "",
            location=self.location or "",
            summary=self.summary or "",
            skills=set(self.skills or []),
            job_titles=list(self.job_titles or []),
            experience_years=self.experience_years or 0,
            education=list(self.education or []),
            keywords=list(self.keywords or []),
            raw_text=self.raw_text or "",
        )
