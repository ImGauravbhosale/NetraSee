from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="NETRASEE_")

    database_url: str = "postgresql+asyncpg://netrasee:netrasee@localhost:5432/netrasee"
    session_secret: str = "dev-only-change-me-in-production"
    session_cookie_name: str = "netrasee_session"
    csrf_cookie_name: str = "netrasee_csrf"
    session_ttl_hours: int = 24 * 7
    cookie_secure: bool = False  # set True behind HTTPS in production
    evidence_storage_dir: str = "/data/evidence"
    max_evidence_upload_mb: int = 25
    login_rate_limit_attempts: int = 8
    login_rate_limit_window_minutes: int = 15


settings = Settings()
