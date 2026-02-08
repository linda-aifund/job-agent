"""Shared FastAPI dependencies — DB session and auth context."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from job_agent.models import SessionLocal, User


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session) -> User | None:
    """Return the logged-in User or None (reads session cookie)."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
