"""Authentication routes — signup, login, logout."""

from datetime import datetime, timezone

import bcrypt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from job_agent.models import User, UserProfile, UserSettings

from .dependencies import get_db

router = APIRouter()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@router.get("/signup")
def signup_form(request: Request):
    return request.app.state.templates.TemplateResponse(
        "auth/signup.html", {"request": request, "error": None}
    )


@router.post("/signup")
async def signup(request: Request, db: Session = Depends(get_db)):
    form = await request.form()

    name = form.get("name", "").strip()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    confirm = form.get("confirm_password", "")

    # Validation
    if not email or not password:
        return request.app.state.templates.TemplateResponse(
            "auth/signup.html", {"request": request, "error": "Email and password are required."}
        )
    if password != confirm:
        return request.app.state.templates.TemplateResponse(
            "auth/signup.html", {"request": request, "error": "Passwords do not match."}
        )
    if len(password) < 8:
        return request.app.state.templates.TemplateResponse(
            "auth/signup.html", {"request": request, "error": "Password must be at least 8 characters."}
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return request.app.state.templates.TemplateResponse(
            "auth/signup.html", {"request": request, "error": "An account with this email already exists."}
        )

    user = User(name=name, email=email, password_hash=_hash_password(password))
    db.add(user)
    db.flush()

    # Create empty profile and default settings
    db.add(UserProfile(user_id=user.id))
    db.add(UserSettings(user_id=user.id))
    db.commit()

    request.session["user_id"] = user.id
    return RedirectResponse("/profile", status_code=303)


@router.get("/login")
def login_form(request: Request):
    return request.app.state.templates.TemplateResponse(
        "auth/login.html", {"request": request, "error": None}
    )


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()

    email = form.get("email", "").strip().lower()
    password = form.get("password", "")

    user = db.query(User).filter(User.email == email).first()
    if not user or not _verify_password(password, user.password_hash):
        return request.app.state.templates.TemplateResponse(
            "auth/login.html", {"request": request, "error": "Invalid email or password."}
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
