"""FastAPI application factory."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from jinja2 import Environment, FileSystemLoader

from job_agent.models import SessionLocal, User

from .dependencies import get_db, get_current_user
from .auth import router as auth_router

WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


def _create_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )


class _Templates:
    """Thin wrapper that mimics Jinja2Templates from starlette."""

    def __init__(self):
        self.env = _create_jinja_env()

    def TemplateResponse(self, name: str, context: dict, status_code: int = 200):
        from starlette.responses import HTMLResponse
        template = self.env.get_template(name)

        # Inject current user into every template context
        request = context.get("request")
        if request and "user" not in context:
            db = SessionLocal()
            try:
                context["user"] = get_current_user(request, db)
            finally:
                db.close()

        html = template.render(**context)
        return HTMLResponse(html, status_code=status_code)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize scheduler and register active schedules
    try:
        from job_agent.scheduler import init_scheduler, schedule_user_pipeline, shutdown_scheduler
        from job_agent.models import UserSettings
        init_scheduler()
        db = SessionLocal()
        try:
            active = db.query(UserSettings).filter(UserSettings.schedule_enabled.is_(True)).all()
            for settings in active:
                schedule_user_pipeline(settings.user_id, settings)
        finally:
            db.close()
    except Exception:
        pass  # Scheduler not yet implemented in early phases

    yield

    # Shutdown
    try:
        from job_agent.scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(title="Job Agent", lifespan=lifespan)

    # Session middleware for cookie-based auth
    secret = os.environ.get("SESSION_SECRET", "dev-secret-change-me-in-production")
    app.add_middleware(SessionMiddleware, secret_key=secret)

    # Static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Templates
    app.state.templates = _Templates()

    # Routers
    app.include_router(auth_router)

    # Lazy-import phase 3+ routers to avoid import errors during early phases
    try:
        from .dashboard import router as dashboard_router
        app.include_router(dashboard_router)
    except ImportError:
        pass
    try:
        from .settings import router as settings_router
        app.include_router(settings_router)
    except ImportError:
        pass
    try:
        from .profile import router as profile_router
        app.include_router(profile_router)
    except ImportError:
        pass
    try:
        from .schedule import router as schedule_router
        app.include_router(schedule_router)
    except ImportError:
        pass

    # Landing page
    @app.get("/")
    def landing(request: Request):
        db = SessionLocal()
        try:
            user = get_current_user(request, db)
        finally:
            db.close()
        if user:
            return RedirectResponse("/dashboard", status_code=303)
        return app.state.templates.TemplateResponse("landing.html", {"request": request})

    return app


app = create_app()
