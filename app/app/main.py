from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.models import User
from app.core.security import hash_password
from app.api.web import router as web_router
from app.api.rest import router as api_router
from app.services.scheduler import start_scheduler, shutdown_scheduler

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db = SessionLocal()
    try:
        admin = db.query(User).count()
        if admin == 0:
            user = User(
                email="admin@example.local",
                full_name="Admin",
                password_hash=hash_password("admin1234"),
                role="admin",
                is_active=True,
            )
            db.add(user)
            db.commit()
            logger.info("created default admin user", extra={"email": user.email})
    finally:
        db.close()

    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie_name,
    https_only=settings.session_https_only,
    same_site="lax",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(web_router)
app.include_router(api_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401 and not request.url.path.startswith("/api") and request.url.path != "/login":
        return RedirectResponse("/login", status_code=303)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/health")
def health():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok"})
    finally:
        db.close()
