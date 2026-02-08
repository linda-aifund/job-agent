"""Profile management routes — resume upload, LinkedIn, skills."""

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from job_agent.models import User, UserProfile

from .dependencies import get_db, get_current_user

router = APIRouter(prefix="/profile")

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads"))


def _require_login(request: Request, db: Session) -> User:
    user = get_current_user(request, db)
    if not user:
        raise _redirect_login()
    return user


def _redirect_login():
    from fastapi import HTTPException
    # We use a trick: raise an HTTPException that the handler converts to redirect
    # Actually, let's just return None and handle in route
    pass


@router.get("")
def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    return request.app.state.templates.TemplateResponse("profile/index.html", {
        "request": request,
        "user": user,
        "profile": profile,
    })


@router.post("/upload-resume")
async def upload_resume(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Validate file type
    if not file.filename or not file.filename.lower().endswith((".pdf", ".txt", ".md")):
        return request.app.state.templates.TemplateResponse("profile/index.html", {
            "request": request,
            "user": user,
            "profile": db.query(UserProfile).filter(UserProfile.user_id == user.id).first(),
            "flash_message": "Please upload a PDF, TXT, or MD file.",
            "flash_type": "error",
        })

    # Save file
    user_dir = UPLOAD_DIR / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse with existing resume parser
    from job_agent.profile.resume_parser import parse_resume
    try:
        parsed = parse_resume(str(dest))
    except Exception as e:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        return request.app.state.templates.TemplateResponse("profile/index.html", {
            "request": request,
            "user": user,
            "profile": profile,
            "flash_message": f"Failed to parse resume: {e}",
            "flash_type": "error",
        })

    # Update profile in DB
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)

    profile.resume_filename = file.filename
    profile.resume_path = str(dest)
    profile.name = parsed.name or profile.name
    profile.phone = parsed.phone or profile.phone
    profile.location = parsed.location or profile.location
    profile.summary = parsed.summary or profile.summary
    profile.skills = sorted(parsed.skills) if parsed.skills else profile.skills or []
    profile.job_titles = parsed.job_titles or profile.job_titles or []
    profile.experience_years = parsed.experience_years or profile.experience_years
    profile.education = parsed.education or profile.education or []
    profile.keywords = parsed.keywords or profile.keywords or []
    profile.raw_text = parsed.raw_text or profile.raw_text
    profile.parsed_at = datetime.now(timezone.utc)
    db.commit()

    return request.app.state.templates.TemplateResponse("profile/index.html", {
        "request": request,
        "user": user,
        "profile": profile,
        "flash_message": f"Resume '{file.filename}' uploaded and parsed successfully.",
        "flash_type": "success",
    })


@router.post("/linkedin")
async def import_linkedin(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    linkedin_url = form.get("linkedin_url", "").strip()

    if not linkedin_url or "linkedin.com/in/" not in linkedin_url:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        return request.app.state.templates.TemplateResponse("profile/index.html", {
            "request": request,
            "user": user,
            "profile": profile,
            "flash_message": "Please enter a valid LinkedIn profile URL.",
            "flash_type": "error",
        })

    from job_agent.profile.linkedin_scraper import scrape_linkedin_profile
    try:
        parsed = scrape_linkedin_profile(linkedin_url)
    except Exception as e:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        return request.app.state.templates.TemplateResponse("profile/index.html", {
            "request": request,
            "user": user,
            "profile": profile,
            "flash_message": f"Failed to scrape LinkedIn: {e}",
            "flash_type": "error",
        })

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)

    profile.linkedin_url = linkedin_url
    profile.name = parsed.name or profile.name
    profile.phone = parsed.phone or profile.phone
    profile.location = parsed.location or profile.location
    profile.summary = parsed.summary or profile.summary
    profile.skills = sorted(parsed.skills) if parsed.skills else profile.skills or []
    profile.job_titles = parsed.job_titles or profile.job_titles or []
    profile.experience_years = parsed.experience_years or profile.experience_years
    profile.education = parsed.education or profile.education or []
    profile.keywords = parsed.keywords or profile.keywords or []
    profile.raw_text = parsed.raw_text or profile.raw_text
    profile.parsed_at = datetime.now(timezone.utc)
    db.commit()

    return request.app.state.templates.TemplateResponse("profile/index.html", {
        "request": request,
        "user": user,
        "profile": profile,
        "flash_message": "LinkedIn profile imported successfully.",
        "flash_type": "success",
    })


@router.post("/skills")
async def update_skills(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    action = form.get("action", "")
    skill = form.get("skill", "").strip().lower()

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        return RedirectResponse("/profile", status_code=303)

    current_skills = list(profile.skills or [])

    if action == "add" and skill and skill not in current_skills:
        current_skills.append(skill)
        current_skills.sort()
    elif action == "remove" and skill in current_skills:
        current_skills.remove(skill)

    profile.skills = current_skills
    db.commit()

    return RedirectResponse("/profile", status_code=303)
