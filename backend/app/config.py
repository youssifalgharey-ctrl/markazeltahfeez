import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
STATIC_DIR = PROJECT_DIR / "public" if (PROJECT_DIR / "public").exists() else PROJECT_DIR / "frontend"
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = (DATA_DIR / "authdb.sqlite3").resolve().as_posix()

class Settings(BaseSettings):
    PORT: int = 8081
    SERVER_PORT: int = 8081
    SERVER_BASE_URL: str = "http://localhost:8081"
    DATABASE_URL: str = f"sqlite:///{DB_PATH}"

    SYNC_WEBHOOK_SECRET: str = "AsserigaQuranSyncSecretKey2026!"
    JWT_SECRET: str = "AsserigaQuranPlatformSecretKey2026Secure!"
    JWT_EXPIRATION_MS: int = 2592000000  # 30 days in ms

    # الـ Origins المسموح بها للـ CORS (مفصولة بفاصلة إذا كانت أكثر من واحد)
    ALLOWED_ORIGINS: str = "http://localhost:8081"

    GOOGLE_SHEETS_WEBHOOK_URL: str = (
        "https://script.google.com/macros/s/AKfycbxsdDNeNDXMP3YpNNK-qDhSDb35JAEv23uP-hR2UkacwUA0cEuKWPmoHa90MO0Ie2rdQQ/exec"
    )

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = "markazeltafeez@gmail.com"
    MAIL_PASSWORD: str = ""
    PAYMENT_ADMIN_EMAIL: str = "markazeltafeez@gmail.com"

    @property
    def allowed_origins_list(self) -> list[str]:
        """تحويل ALLOWED_ORIGINS من نص مفصول بفاصلة إلى قائمة."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = str(BACKEND_DIR / ".env")
        extra = "ignore"

settings = Settings()
