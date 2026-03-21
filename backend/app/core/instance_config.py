"""
Runtime configuration resolver for instance-level settings.

Reads API keys from MongoDB instance_settings (DB overrides set via Admin UI),
falling back to environment variables. DB values are Fernet-encrypted at rest.

Usage:
    from app.core.instance_config import get_config_value, is_x_integration_enabled

    gemini_key = await get_config_value("gemini_api_key")
    x_enabled = await is_x_integration_enabled()
"""

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.database import get_database

logger = logging.getLogger(__name__)

# Derive Fernet key from SECRET_KEY (same derivation as server.py)
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
_fernet = Fernet(_fernet_key)

# DB key → environment variable name mapping
_ENV_KEY_MAP = {
    "gemini_api_key": "GEMINI_API_KEY",
    "x_client_id": "X_CLIENT_ID",
    "x_client_secret": "X_CLIENT_SECRET",
    "x_redirect_uri": "X_REDIRECT_URI",
    "resend_api_key": "RESEND_API_KEY",
}

# Keys that are Fernet-encrypted in the DB
_ENCRYPTED_KEYS = {"gemini_api_key", "x_client_id", "x_client_secret", "resend_api_key"}


async def get_config_value(db_key: str, default: str | None = None) -> str | None:
    """Get a config value: DB override (decrypted) → env var → default."""
    try:
        db = get_database()
        doc = await db.instance_settings.find_one({"_id": "api_keys"}, {db_key: 1})
        if doc and doc.get(db_key):
            if db_key in _ENCRYPTED_KEYS:
                return _fernet.decrypt(doc[db_key].encode()).decode()
            return doc[db_key]
    except Exception:
        logger.debug(f"DB config lookup failed for {db_key}, using env fallback")

    env_key = _ENV_KEY_MAP.get(db_key, db_key.upper())
    return os.environ.get(env_key, default)


async def is_x_integration_enabled() -> bool:
    """Check if X integration is enabled (DB override → env var)."""
    try:
        db = get_database()
        doc = await db.instance_settings.find_one({"_id": "api_keys"}, {"x_integration_enabled": 1})
        if doc and doc.get("x_integration_enabled") is not None:
            return bool(doc["x_integration_enabled"])
    except Exception:
        logger.debug("DB config lookup failed for x_integration_enabled")

    return os.environ.get("X_INTEGRATION_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
    )
