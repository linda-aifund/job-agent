"""Dashboard routes — stats, job list, run history."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from job_agent.models import SeenJob, RunHistory

from .dependencies import get_db, get_current_user

router = APIRouter(prefix="/dashboard")

PER_PAGE = 25


@router.get("")
def dashboard_index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Stats
    total_jobs = db.query(func.count(SeenJob.id)).filter(SeenJob.user_id == user.id).scalar() or 0
    jobs_emailed = db.query(func.count(SeenJob.id)).filter(
        SeenJob.user_id == user.id, SeenJob.sent_at.isnot(None)
    ).scalar() or 0
    total_runs = db.query(func.count(RunHistory.id)).filter(RunHistory.user_id == user.id).scalar() or 0
    last_run = db.query(RunHistory).filter(
        RunHistory.user_id == user.id
    ).order_by(RunHistory.run_at.desc()).first()

    # Recent matched jobs (top 20 by score)
    recent_jobs = db.query(SeenJob).filter(
        SeenJob.user_id == user.id,
        SeenJob.match_score > 0,
    ).order_by(SeenJob.match_score.desc()).limit(20).all()

    return request.app.state.templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "user": user,
        "total_jobs": total_jobs,
        "jobs_emailed": jobs_emailed,
        "total_runs": total_runs,
        "last_run": last_run,
        "recent_jobs": recent_jobs,
    })


@router.get("/jobs")
def jobs_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    page = int(request.query_params.get("page", 1))
    sort = request.query_params.get("sort", "score")
    page = max(1, page)

    query = db.query(SeenJob).filter(SeenJob.user_id == user.id)

    if sort == "date":
        query = query.order_by(SeenJob.first_seen_at.desc())
    elif sort == "source":
        query = query.order_by(SeenJob.source, SeenJob.match_score.desc())
    else:
        query = query.order_by(SeenJob.match_score.desc())

    total = query.count()
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)

    jobs = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return request.app.state.templates.TemplateResponse("dashboard/jobs.html", {
        "request": request,
        "user": user,
        "jobs": jobs,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "sort": sort,
    })


@router.get("/history")
def run_history(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    page = int(request.query_params.get("page", 1))
    page = max(1, page)

    query = db.query(RunHistory).filter(
        RunHistory.user_id == user.id
    ).order_by(RunHistory.run_at.desc())

    total = query.count()
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)

    runs = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return request.app.state.templates.TemplateResponse("dashboard/history.html", {
        "request": request,
        "user": user,
        "runs": runs,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    })
