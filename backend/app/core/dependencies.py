"""
FastAPI dependencies for authentication and rate limiting.

Provides reusable dependency functions for route handlers.
"""

import jwt
from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_database
from app.core.security import decode_token

# Global rate limiter instance
limiter = Limiter(key_func=get_remote_address)


def get_user_identifier(request: Request) -> str:
    """
    Get user ID from auth token, fallback to IP if not authenticated.

    Used for user-based rate limiting to prevent abuse.

    Args:
        request: FastAPI Request object

    Returns:
        String identifier in format "user:{id}" or "ip:{address}"
    """
    try:
        # Try cookies first (primary auth method)
        token = request.cookies.get("access_token")

        # Fallback to Authorization header
        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if token:
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
    except Exception:
        return f"ip:{get_remote_address(request)}"

    # Fallback to IP-based rate limiting
    return f"ip:{get_remote_address(request)}"


async def get_current_user(request: Request) -> dict:
    """
    Dependency function to get current authenticated user from cookies.

    Reads token from cookies with Authorization header fallback.
    Validates token and retrieves user from database.

    Args:
        request: FastAPI Request object

    Returns:
        User dictionary (excluding password_hash)

    Raises:
        HTTPException(401): If not authenticated or token invalid
    """
    token = request.cookies.get("access_token")
    if not token:
        # Fallback to Authorization header for backwards compatibility
        auth_header = request.headers.get("Authorization", "")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_token(token)

        # Verify this is an access token
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        db = get_database()
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    except jwt.ExpiredSignatureError as err:
        raise HTTPException(status_code=401, detail="Token expired") from err
    except jwt.InvalidTokenError as err:
        raise HTTPException(status_code=401, detail="Invalid token") from err


# Alias for backward compatibility
get_current_user_info = get_current_user
