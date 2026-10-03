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
    # Dev-only Fernet key for encrypting connection credentials (GitHub PATs)
    # at rest. Generate a real one per deployment with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    connection_encryption_key: str = "cmVPRTUn_iPADDq4ykjkk2rLu4gPTedozwCzgnkAYgA="
    github_api_base_url: str = "https://api.github.com"


settings = Settings()
