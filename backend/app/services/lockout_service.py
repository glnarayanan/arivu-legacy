"""
Redis-based account lockout service.

Tracks failed login attempts and locks accounts after threshold exceeded.
Fails open on Redis errors (don't block login if Redis is down).
"""

import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level Redis client (lazy initialization)
redis_client = None


async def get_redis():
    """Get or create Redis client for lockout tracking."""
    global redis_client
    if redis_client is None:
        redis_client = await aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        logger.info("Redis client initialized for account lockout tracking")
    return redis_client


async def is_account_locked(email: str) -> bool:
    """Check if account is locked due to too many failed attempts."""
    try:
        r = await get_redis()
        attempts = await r.get(f"login_attempts:{email}")
        return attempts is not None and int(attempts) >= settings.LOCKOUT_THRESHOLD
    except Exception as e:
        logger.exception(f"Redis error checking lockout for {email}")
        return False  # Fail open - don't block login if Redis is down


async def record_failed_login(email: str):
    """Increment failed login counter with expiry."""
    try:
        r = await get_redis()
        key = f"login_attempts:{email}"
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, settings.LOCKOUT_DURATION_SECONDS)
        await pipe.execute()
    except Exception as e:
        logger.exception(f"Redis error recording failed login for {email}")


async def clear_failed_logins(email: str):
    """Clear failed login counter on successful login."""
    try:
        r = await get_redis()
        await r.delete(f"login_attempts:{email}")
    except Exception as e:
        logger.exception(f"Redis error clearing failed logins for {email}")
