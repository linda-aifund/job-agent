"""Settings routes — search, matching, email, API keys, run-now."""

import json
import threading

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from job_agent.models import User, UserSettings

from .dependencies import get_db, get_current_user

router = APIRouter(prefix="/settings")


@router.get("")
def settings_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    return request.app.state.templates.TemplateResponse("settings/index.html", {
        "request": request,
        "user": user,
        "settings": settings,
    })


@router.post("/search")
async def update_search(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()

    # Parse job titles (comma-separated)
    raw_titles = form.get("job_titles", "")
    titles = [t.strip() for t in raw_titles.split(",") if t.strip()]

    settings.job_titles = titles or settings.job_titles
    settings.location = form.get("location", "").strip() or settings.location
    settings.remote_ok = form.get("remote_ok") == "on"
    settings.experience_years = int(form.get("experience_years", 0) or 0)
    settings.max_results_per_source = int(form.get("max_results_per_source", 50) or 50)
    settings.score_threshold = float(form.get("score_threshold", 0.3) or 0.3)
    settings.use_ai_matching = form.get("use_ai_matching") == "on"
    settings.ai_pre_filter_threshold = float(form.get("ai_pre_filter_threshold", 0.2) or 0.2)
    db.commit()

    return request.app.state.templates.TemplateResponse("settings/index.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "flash_message": "Search & matching settings saved.",
        "flash_type": "success",
    })


@router.post("/email")
async def update_email(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()

    settings.smtp_server = form.get("smtp_server", "").strip() or settings.smtp_server
    settings.smtp_port = int(form.get("smtp_port", 587) or 587)
    settings.sender_email = form.get("sender_email", "").strip()
    # Only update password if a new one is provided
    new_password = form.get("sender_password", "").strip()
    if new_password:
        settings.sender_password = new_password
    settings.recipient_email = form.get("recipient_email", "").strip()
    db.commit()

    return request.app.state.templates.TemplateResponse("settings/index.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "flash_message": "Email settings saved.",
        "flash_type": "success",
    })


@router.post("/api-keys")
async def update_api_keys(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()

    new_serpapi = form.get("serpapi_key", "").strip()
    if new_serpapi:
        settings.serpapi_key = new_serpapi
    new_openai = form.get("openai_api_key", "").strip()
    if new_openai:
        settings.openai_api_key = new_openai
    db.commit()

    return request.app.state.templates.TemplateResponse("settings/index.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "flash_message": "API keys saved.",
        "flash_type": "success",
    })


@router.post("/run-now")
def run_now(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    from job_agent.pipeline import run_pipeline_for_user

    def _run_with_error_capture(uid):
        import logging
        import time
        logger = logging.getLogger("job_agent.pipeline")
        try:
            run_pipeline_for_user(uid)
        except Exception as e:
            logger.error("[user:%d] Run Now thread crashed: %s", uid, e, exc_info=True)
            # Record the crash in run history so user can see it
            try:
                from job_agent.models import SessionLocal, RunHistory
                err_db = SessionLocal()
                err_db.add(RunHistory(
                    user_id=uid,
                    error_message=f"Pipeline crashed: {e}",
                    duration_seconds=0,
                ))
                err_db.commit()
                err_db.close()
            except Exception:
                pass

    thread = threading.Thread(target=_run_with_error_capture, args=(user.id,), daemon=True)
    thread.start()

    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    return request.app.state.templates.TemplateResponse("settings/index.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "flash_message": "Pipeline run started in the background. Check the Dashboard for results.",
        "flash_type": "success",
    })
