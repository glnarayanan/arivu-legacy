"""
Tests for auth router endpoints.

Covers: signup, login, logout, refresh, password management, profile CRUD, avatar.
Uses auth_client (no auth override) for auth flow tests and client (with auth
override) for authenticated profile/password endpoints.
"""

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password

UTC = timezone.utc

# ============================================
# Auth Endpoint Tests (auth_client -- no auth override)
# ============================================


@pytest.mark.anyio
async def test_signup_disabled(auth_client):
    """POST /api/auth/signup returns 403 because signups are disabled."""
    original = settings.SIGNUPS_ENABLED
    settings.SIGNUPS_ENABLED = False
    try:
        response = await auth_client.post(
            "/api/auth/signup",
            json={
                "email": "new@example.com",
                "password": "ValidPass1!",
                "name": "New User",
            },
        )
    finally:
        settings.SIGNUPS_ENABLED = original

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_login_success(auth_client, mock_db):
    """POST /api/auth/login with valid credentials returns 200 and sets cookies."""
    test_password = "ValidPass1!"
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "password_hash": hash_password(test_password),
        }
    )

    with (
        patch(
            "app.routers.auth.is_account_locked",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.routers.auth.clear_failed_logins",
            new_callable=AsyncMock,
        ),
    ):
        response = await auth_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": test_password},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "test@example.com"
    # Verify cookies are set
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


@pytest.mark.anyio
async def test_cli_login_success(auth_client, mock_db):
    """POST /api/auth/cli/login returns bearer tokens for CLI clients."""
    test_password = "ValidPass1!"
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "password_hash": hash_password(test_password),
        }
    )

    with (
        patch(
            "app.routers.auth.is_account_locked",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.routers.auth.clear_failed_logins",
            new_callable=AsyncMock,
        ),
    ):
        response = await auth_client.post(
            "/api/auth/cli/login",
            json={"email": "test@example.com", "password": test_password},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == "test@example.com"
    assert data["access_token_expires_at"]
    assert data["refresh_token_expires_at"]


@pytest.mark.anyio
async def test_login_invalid_credentials(auth_client, mock_db):
    """POST /api/auth/login with wrong password returns 401."""
    mock_db.users.find_one = AsyncMock(return_value=None)

    with (
        patch(
            "app.routers.auth.is_account_locked",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.routers.auth.record_failed_login",
            new_callable=AsyncMock,
        ),
    ):
        response = await auth_client.post(
            "/api/auth/login",
            json={"email": "wrong@example.com", "password": "WrongPass1!"},
        )

    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.anyio
async def test_cli_refresh_success(auth_client, mock_db):
    """POST /api/auth/cli/refresh returns rotated bearer tokens."""
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "password_hash": hash_password("ValidPass1!"),
        }
    )

    refresh_token = create_refresh_token({"sub": "user-123"})

    response = await auth_client.post(
        "/api/auth/cli/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["id"] == "user-123"


@pytest.mark.anyio
async def test_cli_refresh_rejects_access_token(auth_client, mock_db):
    """POST /api/auth/cli/refresh rejects access tokens."""
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "password_hash": hash_password("ValidPass1!"),
        }
    )

    access_token = create_access_token({"sub": "user-123"})

    response = await auth_client.post(
        "/api/auth/cli/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401
    assert "Invalid token type" in response.json()["detail"]


@pytest.mark.anyio
async def test_login_locked_account(auth_client, mock_db):
    """POST /api/auth/login on locked account returns 401 with same message."""
    with patch(
        "app.routers.auth.is_account_locked",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = await auth_client.post(
            "/api/auth/login",
            json={"email": "locked@example.com", "password": "ValidPass1!"},
        )

    assert response.status_code == 401
    # Same message as invalid credentials to prevent enumeration
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.anyio
async def test_logout(auth_client):
    """POST /api/auth/logout returns 200 and clears cookies."""
    response = await auth_client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
    # Check Set-Cookie headers indicate deletion (max-age=0 or empty value)
    set_cookie_headers = response.headers.get_list("set-cookie")
    cookie_names = [h.split("=")[0].strip() for h in set_cookie_headers]
    assert "access_token" in cookie_names
    assert "refresh_token" in cookie_names


@pytest.mark.anyio
async def test_refresh_noop(auth_client):
    """POST /api/auth/refresh returns 200 (no-op endpoint)."""
    response = await auth_client.post("/api/auth/refresh")
    assert response.status_code == 200


# ============================================
# Password Management Tests (auth_client -- no auth override)
# ============================================


@pytest.mark.anyio
async def test_forgot_password_existing_user(auth_client, mock_db):
    """POST /api/auth/forgot-password for existing user returns generic success."""
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "user-123",
            "email": "test@example.com",
            "name": "Test User",
        }
    )
    mock_db.password_reset_tokens.delete_many = AsyncMock()
    mock_db.password_reset_tokens.insert_one = AsyncMock()

    with patch(
        "app.routers.auth.send_password_reset_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = await auth_client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"},
        )

    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]


@pytest.mark.anyio
async def test_forgot_password_nonexistent_user(auth_client, mock_db):
    """POST /api/auth/forgot-password for non-existent user returns SAME generic message."""
    mock_db.users.find_one = AsyncMock(return_value=None)

    response = await auth_client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )

    assert response.status_code == 200
    # Same message as existing user to prevent enumeration
    assert "If an account exists" in response.json()["message"]


@pytest.mark.anyio
async def test_reset_password_valid_token(auth_client, mock_db):
    """POST /api/auth/reset-password with valid token updates password."""
    future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    mock_db.password_reset_tokens.find_one = AsyncMock(
        return_value={
            "id": "token-123",
            "user_id": "user-123",
            "token": "valid-token-abc",
            "expires_at": future_time,
        }
    )
    mock_db.users.update_one = AsyncMock()
    mock_db.password_reset_tokens.delete_one = AsyncMock()

    response = await auth_client.post(
        "/api/auth/reset-password",
        json={"token": "valid-token-abc", "new_password": "NewValidPass1!"},
    )

    assert response.status_code == 200
    assert "successfully" in response.json()["message"].lower()
    mock_db.users.update_one.assert_called_once()
    mock_db.password_reset_tokens.delete_one.assert_called_once()


@pytest.mark.anyio
async def test_reset_password_expired_token(auth_client, mock_db):
    """POST /api/auth/reset-password with expired token returns 400."""
    past_time = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    mock_db.password_reset_tokens.find_one = AsyncMock(
        return_value={
            "id": "token-123",
            "user_id": "user-123",
            "token": "expired-token",
            "expires_at": past_time,
        }
    )
    mock_db.password_reset_tokens.delete_one = AsyncMock()

    response = await auth_client.post(
        "/api/auth/reset-password",
        json={"token": "expired-token", "new_password": "NewValidPass1!"},
    )

    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_reset_password_invalid_token(auth_client, mock_db):
    """POST /api/auth/reset-password with invalid token returns 400."""
    mock_db.password_reset_tokens.find_one = AsyncMock(return_value=None)

    response = await auth_client.post(
        "/api/auth/reset-password",
        json={"token": "nonexistent-token", "new_password": "NewValidPass1!"},
    )

    assert response.status_code == 400


# ============================================
# Profile Tests (client -- has auth override)
# ============================================


@pytest.mark.anyio
async def test_get_auth_me(client):
    """GET /api/auth/me returns current user info."""
    response = await client.get("/api/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-user-id"
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"


@pytest.mark.anyio
async def test_change_password_success(client, mock_db):
    """POST /api/auth/change-password with correct current password succeeds."""
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "test-user-id",
            "email": "test@example.com",
            "password_hash": hash_password("OldPass1!"),
        }
    )
    mock_db.users.update_one = AsyncMock()

    with patch(
        "app.routers.auth.verify_password",
        return_value=True,
    ):
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPass1!",
                "new_password": "NewValidPass1!",
            },
        )

    assert response.status_code == 200
    assert "successfully" in response.json()["message"].lower()


@pytest.mark.anyio
async def test_change_password_wrong_current(client, mock_db):
    """POST /api/auth/change-password with wrong current password returns 400."""
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "test-user-id",
            "email": "test@example.com",
            "password_hash": hash_password("RealPass1!"),
        }
    )

    with patch(
        "app.routers.auth.verify_password",
        return_value=False,
    ):
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPass1!",
                "new_password": "NewValidPass1!",
            },
        )

    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_get_profile(client, mock_db):
    """GET /api/user/profile returns user profile data."""
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "test-user-id",
            "email": "test@example.com",
            "name": "Test User",
        }
    )

    response = await client.get("/api/user/profile")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.anyio
async def test_update_profile(client, mock_db):
    """PUT /api/user/profile updates name and returns updated user."""
    # When updating only name (no email), find_one is called once at the end
    # to return the updated user. No duplicate email check occurs.
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "test-user-id",
            "email": "test@example.com",
            "name": "Updated Name",
        }
    )
    mock_db.users.update_one = AsyncMock()

    response = await client.put(
        "/api/user/profile",
        json={"name": "Updated Name"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"


@pytest.mark.anyio
async def test_update_profile_duplicate_email(client, mock_db):
    """PUT /api/user/profile with taken email returns 400."""
    # find_one returns an existing user (email taken by another user)
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "other-user-id",
            "email": "taken@example.com",
        }
    )

    response = await client.put(
        "/api/user/profile",
        json={"email": "taken@example.com"},
    )

    assert response.status_code == 400
    assert "already in use" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_upload_avatar(client, mock_db):
    """POST /api/user/avatar with valid small image succeeds."""
    # Create a small valid base64 string (tiny 1x1 PNG)
    small_data = base64.b64encode(b"\x89PNG" + b"\x00" * 100).decode()
    mock_db.users.update_one = AsyncMock()

    response = await client.post(
        "/api/user/avatar",
        json={"avatar_data": small_data},
    )

    assert response.status_code == 200
    assert "successfully" in response.json()["message"].lower()


@pytest.mark.anyio
async def test_upload_avatar_too_large(client, mock_db):
    """POST /api/user/avatar with oversized image returns 400."""
    # Create base64 data that exceeds 1.5MB when decoded
    large_bytes = b"\x00" * (2 * 1024 * 1024)  # 2MB
    large_data = base64.b64encode(large_bytes).decode()

    response = await client.post(
        "/api/user/avatar",
        json={"avatar_data": large_data},
    )

    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_delete_avatar(client, mock_db):
    """DELETE /api/user/avatar removes avatar successfully."""
    mock_db.users.update_one = AsyncMock()

    response = await client.delete("/api/user/avatar")

    assert response.status_code == 200
    assert "removed" in response.json()["message"].lower()
    mock_db.users.update_one.assert_called_once()
