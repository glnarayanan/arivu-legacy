"""
Core module - shared infrastructure for the Arivu backend.

Re-exports commonly used functions and classes for convenience.
"""

from app.core.config import get_settings, settings
from app.core.database import close_db, get_database, init_db
from app.core.dependencies import (
    get_current_user,
    get_current_user_info,
    get_user_identifier,
    limiter,
)
from app.core.middleware import (
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)

__all__ = [
    # Config
    "settings",
    "get_settings",
    # Database
    "init_db",
    "close_db",
    "get_database",
    # Security
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_password",
    "hash_password",
    "validate_password_strength",
    # Dependencies
    "limiter",
    "get_user_identifier",
    "get_current_user",
    "get_current_user_info",
    # Middleware
    "RequestSizeLimitMiddleware",
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
]
