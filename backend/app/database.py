from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings, DATA_DIR, PROJECT_DIR

# Resolve and normalize DB URL
db_url = settings.DATABASE_URL

# Fix SQLAlchemy compatibility for postgres:// provided by services like Render/Supabase/Heroku/Neon
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if db_url.startswith("sqlite:///"):
    try:
        raw_path = db_url.replace("sqlite:///", "")
        p = Path(raw_path)
        if not p.is_absolute():
            cleaned_rel = raw_path.replace("\\", "/").lstrip("./")
            abs_p = (PROJECT_DIR / cleaned_rel).resolve()
            abs_p.parent.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{abs_p.as_posix()}"
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{p.as_posix()}"
    except OSError:
        # Fallback to /tmp on serverless environments with read-only root filesystems
        db_url = "sqlite:////tmp/authdb.sqlite3"

# Engine options
engine_kwargs = {}
if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL connection pool settings for concurrent users
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 30
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 1800

engine = create_engine(
    db_url,
    echo=False,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
