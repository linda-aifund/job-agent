"""Schedule routes — configure pipeline schedule."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from job_agent.models import UserSettings
from job_agent.scheduler import schedule_user_pipeline, get_next_run_time, get_scheduler_info

from .dependencies import get_db, get_current_user

router = APIRouter(prefix="/schedule")


@router.get("")
def schedule_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    next_run = get_next_run_time(user.id)

    return request.app.state.templates.TemplateResponse("schedule/index.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "next_run": next_run,
    })


@router.post("")
async def update_schedule(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()

    settings.schedule_enabled = form.get("schedule_enabled") == "on"
    settings.schedule_frequency = form.get("schedule_frequency", "weekly")
    settings.schedule_day_of_week = form.get("schedule_day_of_week", "mon")
    settings.schedule_day_of_month = int(form.get("schedule_day_of_month", 1) or 1)
    settings.schedule_hour = int(form.get("schedule_hour", 9) or 9)
    settings.schedule_minute = int(form.get("schedule_minute", 0) or 0)
    settings.schedule_timezone = form.get("schedule_timezone", "America/New_York").strip()
    db.commit()

    # Sync with APScheduler
    schedule_user_pipeline(user.id, settings)
    next_run = get_next_run_time(user.id)

    return request.app.state.templates.TemplateResponse("schedule/index.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "next_run": next_run,
        "flash_message": "Schedule updated." + (f" Next run: {next_run.strftime('%Y-%m-%d %H:%M %Z')}" if next_run else ""),
        "flash_type": "success",
    })


@router.get("/debug")
def schedule_debug(request: Request, db: Session = Depends(get_db)):
    """Diagnostic endpoint — shows scheduler state."""
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "not logged in"}, status_code=401)
    info = get_scheduler_info()
    return JSONResponse(info)
