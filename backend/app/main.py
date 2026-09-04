import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.config import settings, STATIC_DIR
from app.database import engine, Base, SessionLocal
from app.seeder import seed_admin_accounts
from app.scheduler.tasks import start_scheduler, check_expiring_and_expired_subscriptions
from app.security.rate_limiter import RateLimitMiddleware

# Routers
from app.routers import (
    auth,
    payment,
    ijaza,
    admin,
    progress,
    leaderboard,
    exam,
    quiz,
    plan,
    beginner_plan,
    tajweed,
    usul,
    notification,
    db_console,
    ai_chat,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── تحديد بيئة التشغيل ──────────────────────────────────────────────
IS_PRODUCTION = os.getenv("ENV", "development").lower() == "production"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    logger.info("Seeding admin accounts...")
    db = SessionLocal()
    try:
        seed_admin_accounts(db)
    finally:
        db.close()

    try:
        logger.info("Starting background scheduler...")
        start_scheduler()
    except Exception as e:
        logger.warning("Background scheduler could not be started: %s", e)

    logger.info("Running initial startup subscription check...")
    try:
        check_expiring_and_expired_subscriptions()
    except Exception as e:
        logger.error("Startup subscription check error: %s", e)

    yield

    # Shutdown
    logger.info("Server shutting down...")

app = FastAPI(
    title="Quran Platform Backend API",
    description="Python FastAPI backend replacing Spring Boot for the Quran Platform",
    version="2.0.0",
    lifespan=lifespan,
    # تعطيل مستندات Swagger في بيئة الإنتاج
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# ── Security Headers Middleware ──────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Rate Limiting
app.add_middleware(RateLimitMiddleware)

# CORS — مقيّد بالـ origins المسموح بها فقط (لا يُسمح بـ wildcard مع credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(payment.router)
app.include_router(ijaza.router)
app.include_router(admin.router)
app.include_router(progress.router)
app.include_router(leaderboard.router)
app.include_router(exam.router)
app.include_router(quiz.router)
app.include_router(plan.router)
app.include_router(beginner_plan.router)
app.include_router(tajweed.router)
app.include_router(usul.router)
app.include_router(notification.router)
app.include_router(db_console.router)
app.include_router(ai_chat.router)

# Mount frontend static files
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    logger.info("Mounted static frontend files from: %s", STATIC_DIR)
else:
    logger.warning("Static directory not found at: %s", STATIC_DIR)
