"""
Authentication and user profile router.

Handles registration, login, logout, password management, and user profiles.
Uses HTTP-only cookies for token storage with rate limiting on sensitive endpoints.
"""

import base64
import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, validator

from app.core.config import settings
from app.core.database import get_database
from app.core.dependencies import get_current_user, limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.services.email_service import send_password_reset_email
from app.services.lockout_service import (
    clear_failed_logins,
    is_account_locked,
    record_failed_login,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# ============================================
# Pydantic Models
# ============================================


class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: str

    @validator("name")
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Name cannot be empty")
        if len(v) > 100:
            raise ValueError("Name too long (max 100 characters)")
        if not re.match(r"^[\w\s\-\.]+$", v):
            raise ValueError("Name contains invalid characters")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[dict] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

    @validator("name")
    def validate_name(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Name cannot be empty")
            if len(v) > 100:
                raise ValueError("Name too long (max 100 characters)")
            if not re.match(r"^[\w\s\-\.]+$", v):
                raise ValueError("Name contains invalid characters")
            return v.strip()
        return v


class AvatarUpload(BaseModel):
    avatar_data: str  # Base64 encoded image data


# ============================================
# Auth Endpoints
# ============================================


@router.post("/auth/signup", response_model=TokenResponse)
@limiter.limit("3/hour")
async def signup(request: Request, user_data: UserSignup):
    """Register a new user with password validation"""
    # SIGNUPS DISABLED: Only existing users can login
    # To re-enable signups, remove or comment out the following block
    logger.info(f"Signup attempt blocked (signups disabled): {user_data.email}")
    raise HTTPException(
        status_code=403,
        detail="Signups are currently disabled. Only existing users can log in.",
    )

    # Validate password strength
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        logger.info(f"Signup failed: weak password for email {user_data.email}")
        raise HTTPException(status_code=400, detail=error_msg)

    db = get_database()

    # Check if email already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        logger.info(f"Signup failed: email already registered {user_data.email}")
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    user = {
        "id": str(uuid.uuid4()),
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": hash_password(user_data.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)

    # Create tokens
    access_token = create_access_token(data={"sub": user["id"]})
    refresh_token = create_refresh_token(data={"sub": user["id"]})

    user_response = {"id": user["id"], "email": user["email"], "name": user["name"]}
    logger.info(f"User registered successfully: {user['id']}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_response,
    }


@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, login_data: UserLogin, response: Response):
    """Authenticate user and return tokens as HTTP-only cookies"""
    # Normalize email for lockout tracking
    email_lower = login_data.email.lower()

    # Check lockout BEFORE credential validation (prevents enumeration)
    if await is_account_locked(email_lower):
        logger.warning(f"Login attempt on locked account: {email_lower}")
        # Same message as invalid credentials to prevent enumeration
        raise HTTPException(status_code=401, detail="Invalid credentials")

    db = get_database()

    user = await db.users.find_one({"email": login_data.email})
    if user and user.get("banned"):
        raise HTTPException(status_code=403, detail="Account has been suspended")
    if user and user.get("invite_pending"):
        raise HTTPException(
            status_code=403,
            detail="Please complete your account setup using the invite link sent to your email."
        )
    if not user or not verify_password(login_data.password, user["password_hash"]):
        await record_failed_login(email_lower)
        logger.warning(f"Login failed: invalid credentials for {login_data.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Clear failed attempts on successful login
    await clear_failed_logins(email_lower)

    # Create tokens
    access_token = create_access_token(data={"sub": user["id"]})
    refresh_token = create_refresh_token(data={"sub": user["id"]})

    user_response = {"id": user["id"], "email": user["email"], "name": user["name"]}
    logger.info(f"User logged in successfully: {user['id']}")

    # Set HTTP-only cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    return {"token_type": "bearer", "user": user_response}


@router.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info from cookies"""
    return current_user


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user by clearing cookies"""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")

    return {"message": "Logged out successfully"}


@router.post("/auth/refresh")
async def refresh_token_endpoint(request: Request):
    """Simple refresh endpoint - client's axios interceptor handles rotation"""
    # This endpoint is kept for backwards compatibility
    # The actual refresh logic is handled by client-side axios interceptor
    pass


# ============================================
# Password Reset Endpoints
# ============================================


@router.post("/auth/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(request: Request, reset_request: PasswordResetRequest):
    """Request a password reset email"""
    email = reset_request.email.lower()

    db = get_database()

    # Always return success to prevent email enumeration attacks
    user = await db.users.find_one({"email": email})
    if not user:
        logger.info(f"Password reset requested for non-existent email: {email}")
        return {"message": "If an account exists with this email, you will receive a reset link."}

    # Generate secure reset token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)

    # Store token in database
    await db.password_reset_tokens.delete_many({"user_id": user["id"]})  # Remove old tokens
    await db.password_reset_tokens.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "token": reset_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Send email
    await send_password_reset_email(email, reset_token)

    logger.info(f"Password reset token generated for user: {user['id']}")
    return {"message": "If an account exists with this email, you will receive a reset link."}


@router.post("/auth/reset-password")
@limiter.limit("5/hour")
async def reset_password(request: Request, reset_confirm: PasswordResetConfirm):
    """Reset password using token from email"""
    db = get_database()

    # Find valid token
    token_doc = await db.password_reset_tokens.find_one({"token": reset_confirm.token})
    if not token_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Check expiry
    expires_at = datetime.fromisoformat(token_doc["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await db.password_reset_tokens.delete_one({"token": reset_confirm.token})
        raise HTTPException(status_code=400, detail="Reset token has expired")

    # Validate new password strength
    is_valid, error_msg = validate_password_strength(reset_confirm.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Update password
    new_hash = hash_password(reset_confirm.new_password)
    await db.users.update_one(
        {"id": token_doc["user_id"]},
        {"$set": {"password_hash": new_hash, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    # Delete used token
    await db.password_reset_tokens.delete_one({"token": reset_confirm.token})

    logger.info(f"Password reset completed for user: {token_doc['user_id']}")
    return {"message": "Password reset successfully. You can now log in with your new password."}


@router.post("/auth/change-password")
async def change_password(
    change_request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Change password while logged in (requires current password)"""
    db = get_database()

    # Verify current password
    user = await db.users.find_one({"id": current_user["id"]})
    if not user or not verify_password(change_request.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate new password strength
    is_valid, error_msg = validate_password_strength(change_request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Update password
    new_hash = hash_password(change_request.new_password)
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"password_hash": new_hash, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    logger.info(f"Password changed for user: {current_user['id']}")
    return {"message": "Password changed successfully"}


# ============================================
# User Profile Endpoints
# ============================================


@router.get("/user/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    db = get_database()
    user = await db.users.find_one(
        {"id": current_user["id"]},
        {"_id": 0, "password_hash": 0}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/user/profile")
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile (name, email)"""
    db = get_database()
    update_data = {}

    if profile_update.name is not None:
        update_data["name"] = profile_update.name

    if profile_update.email is not None:
        # Check if email is already taken by another user
        new_email = profile_update.email.lower()
        existing = await db.users.find_one({"email": new_email, "id": {"$ne": current_user["id"]}})
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_data["email"] = new_email

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": update_data}
    )

    logger.info(f"Profile updated for user: {current_user['id']}")

    # Return updated user
    user = await db.users.find_one(
        {"id": current_user["id"]},
        {"_id": 0, "password_hash": 0}
    )
    return user


@router.post("/user/avatar")
async def upload_avatar(
    avatar_upload: AvatarUpload,
    current_user: dict = Depends(get_current_user)
):
    """Upload user avatar (base64 encoded, max 1.5MB)"""
    db = get_database()
    avatar_data = avatar_upload.avatar_data

    # Remove data URL prefix if present
    if avatar_data.startswith("data:"):
        # Extract base64 part after the comma
        if "," in avatar_data:
            avatar_data = avatar_data.split(",", 1)[1]

    # Validate size (1.5MB limit after base64 encoding ~= 2MB base64 string)
    try:
        decoded = base64.b64decode(avatar_data)
        if len(decoded) > 1.5 * 1024 * 1024:  # 1.5MB
            raise HTTPException(status_code=400, detail="Avatar image too large (max 1.5MB)")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=400, detail="Invalid image data")

    # Store as data URL
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "avatar_url": avatar_upload.avatar_data,  # Store original with data URL prefix
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    logger.info(f"Avatar uploaded for user: {current_user['id']}")
    return {"message": "Avatar uploaded successfully"}


@router.delete("/user/avatar")
async def delete_avatar(current_user: dict = Depends(get_current_user)):
    """Remove user avatar"""
    db = get_database()
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$unset": {"avatar_url": ""}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    logger.info(f"Avatar removed for user: {current_user['id']}")
    return {"message": "Avatar removed successfully"}
