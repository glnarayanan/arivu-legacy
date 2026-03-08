"""
Configuration module using Pydantic Settings.

Provides typed settings from environment variables with validation.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Compute project root (backend dir): core -> app -> backend
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),  # Absolute path to project root .env
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars not in Settings
    )

    # Database
    MONGO_URL: str
    DB_NAME: str = "arivu_db"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1

    # Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Email (Resend)
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: str = "noreply@arivu.app"
    APP_URL: str = "https://arivu.app"

    # AI
    GEMINI_API_KEY: Optional[str] = None

    # X (Twitter) Integration
    X_INTEGRATION_ENABLED: bool = False
    X_CLIENT_ID: Optional[str] = None
    X_CLIENT_SECRET: Optional[str] = None
    X_REDIRECT_URI: Optional[str] = None

    # Admin
    ADMIN_EMAILS: str = ""

    # CORS
    CORS_ORIGINS: str = "*"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Account lockout
    LOCKOUT_THRESHOLD: int = 5
    LOCKOUT_DURATION_SECONDS: int = 900  # 15 minutes

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure SECRET_KEY is at least 32 characters."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to avoid re-validating on every call.
    """
    return Settings()


# Convenience alias for direct import
settings = get_settings()
