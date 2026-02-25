from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Traccia Formazione")
    environment: str = os.getenv("ENVIRONMENT", "production")
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://traccia:traccia@db:5432/traccia_formazione",
    )
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "tf_session")
    session_https_only: bool = os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true"
    upload_dir: str = os.getenv("UPLOAD_DIR", "/data/uploads")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))

    factorial_base_url: str = os.getenv("FACTORIAL_BASE_URL", "")
    factorial_api_token: str = os.getenv("FACTORIAL_API_TOKEN", "")
    factorial_company_id: str = os.getenv("FACTORIAL_COMPANY_ID", "")
    factorial_sync_cron: str = os.getenv("FACTORIAL_SYNC_CRON", "0 2 * * *")

    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_tls: bool = os.getenv("SMTP_TLS", "true").lower() == "true"

    webhook_url: str = os.getenv("WEBHOOK_URL", "")
    cors_origins: str = os.getenv("CORS_ORIGINS", "")

    login_rate_limit_attempts: int = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", "10"))
    login_rate_limit_window_seconds: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
