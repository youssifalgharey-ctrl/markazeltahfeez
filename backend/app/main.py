import sys
import os
from pathlib import Path

# Ensure backend directory is in sys.path for serverless runtimes
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import logging
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
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
    # تشغيل تهيئة الجداول والمهام فقط إذا طُلب ذلك أو في البيئة المحلية لتسريع استجابة السيرفر
    if not IS_PRODUCTION or os.getenv("INIT_DB", "false").lower() == "true":
        try:
            Base.metadata.create_all(bind=engine)
            try:
                from sqlalchemy import text
                with engine.connect() as conn:
                    res = conn.execute(text("PRAGMA table_info(APP_USER)"))
                    existing_cols = [row[1] for row in res.fetchall()]
                    if existing_cols:
                        if "active_session_id" not in existing_cols:
                            conn.execute(text("ALTER TABLE APP_USER ADD COLUMN active_session_id VARCHAR"))
                        if "last_active_at" not in existing_cols:
                            conn.execute(text("ALTER TABLE APP_USER ADD COLUMN last_active_at TIMESTAMP"))
                        conn.commit()
            except Exception as mig_err:
                logger.warning("Auto-migration check notice: %s", mig_err)

            db = SessionLocal()
            seed_admin_accounts(db)
            db.close()
        except Exception as e:
            logger.error("DB init error: %s", e)

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

# ── معالجة أخطاء التحقق (Validation Errors) وإرجاع نصوص عربية واضحة بدلاً من كائنات [object Object] ──
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    messages = []
    for err in errors:
        msg = err.get("msg", "")
        # إزالة بادئة "Value error, " التي يضيفها Pydantic تلقائياً
        clean_msg = re.sub(r"^Value error,\s*", "", str(msg), flags=re.IGNORECASE)
        messages.append(clean_msg)
    joined_msg = " - ".join(messages) if messages else "بيانات غير صالحة، يرجى مراجعة المدخلات"
    return JSONResponse(
        status_code=400,
        content={"detail": joined_msg, "message": joined_msg}
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

    # تفعيل الكاش لملفات الفيديو والوسائط الثابتة للتحميل الفوري من كاش المتصفح
    path = request.url.path
    if path.startswith("/video/") or path.endswith((".mp4", ".webm", ".webp")):
        response.headers["Cache-Control"] = "public, max-age=2592000, immutable"

    return response

# Rate Limiting
app.add_middleware(RateLimitMiddleware)

# CORS — السماح بنطاقات Vercel والـ localhost
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.now\.sh|http://localhost:.*",
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
