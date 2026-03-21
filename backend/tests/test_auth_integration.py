"""
Integration tests for authentication flow.

These tests verify the full auth lifecycle works end-to-end:
1. Login sets proper HTTP-only cookies
2. Authenticated requests work with cookies from login
3. Logout clears cookies
4. Subsequent requests are rejected after logout

Uses a persistent AsyncClient session that tracks cookies automatically.
Each test creates its own app and client for complete isolation.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.dependencies import limiter
from app.core.security import hash_password
from app.routers.auth import router as auth_router
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient


def _create_test_app(mock_db):
    """Create an isolated test app with auth router and mock database."""
    test_app = FastAPI()
    api_router = APIRouter(prefix="/api")
    api_router.include_router(auth_router)
    test_app.include_router(api_router)

    # Set up rate limiter
    test_app.state.limiter = limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Override database
    import app.core.database as db_module

    _original_db = db_module.db
    db_module.db = mock_db

    return test_app, _original_db


def _create_mock_db():
    """Create a fresh mock database for integration tests."""
    db = MagicMock()
    db.users = MagicMock()
    db.users.find_one = AsyncMock()
    db.users.insert_one = AsyncMock()
    db.users.update_one = AsyncMock()
    db.password_reset_tokens = MagicMock()
    db.password_reset_tokens.find_one = AsyncMock()
    db.password_reset_tokens.insert_one = AsyncMock()
    db.password_reset_tokens.delete_one = AsyncMock()
    db.password_reset_tokens.delete_many = AsyncMock()
    return db


TEST_PASSWORD = "ValidPass1!"
TEST_USER = {
    "id": "user-integration-123",
    "email": "integration@example.com",
    "name": "Integration User",
    "password_hash": hash_password(TEST_PASSWORD),
}


def _auth_cookie_header(response) -> dict[str, str]:
    access_token = response.cookies.get("access_token")
    refresh_token = response.cookies.get("refresh_token")
    assert access_token is not None
    assert refresh_token is not None
    return {"Cookie": f"access_token={access_token}; refresh_token={refresh_token}"}


def _make_flexible_find_one(test_user):
    """Create a find_one mock that handles projection filtering."""

    async def flexible_find_one(query, projection=None):
        """Return user with or without password_hash based on projection."""
        if projection and "password_hash" in projection and projection["password_hash"] == 0:
            return {k: v for k, v in test_user.items() if k not in ("password_hash", "_id")}
        return test_user

    return AsyncMock(side_effect=flexible_find_one)


@pytest.mark.anyio
async def test_full_auth_flow():
    """Integration test: login -> /auth/me -> logout -> /auth/me rejected."""
    mock_db = _create_mock_db()
    test_app, _original_db = _create_test_app(mock_db)

    # Set up flexible user mock
    mock_db.users.find_one = _make_flexible_find_one(TEST_USER)

    try:
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
            async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
                # Step 1: Login
                login_response = await client.post(
                    "/api/auth/login",
                    json={
                        "email": "integration@example.com",
                        "password": TEST_PASSWORD,
                    },
                )
                assert login_response.status_code == 200, f"Login failed: {login_response.text}"
                assert "access_token" in login_response.cookies
                assert "refresh_token" in login_response.cookies
                auth_headers = _auth_cookie_header(login_response)

                # Step 2: Authenticated request with cookies
                me_response = await client.get("/api/auth/me", headers=auth_headers)
                assert me_response.status_code == 200, f"/auth/me failed: {me_response.text}"
                me_data = me_response.json()
                assert me_data["id"] == "user-integration-123"
                assert me_data["email"] == "integration@example.com"

                # Step 3: Logout
                logout_response = await client.post("/api/auth/logout", headers=auth_headers)
                assert logout_response.status_code == 200

                # Step 4: Subsequent request should fail (cookies cleared)
                me_after_logout = await client.get("/api/auth/me")
                assert (
                    me_after_logout.status_code == 401
                ), f"Expected 401 after logout, got {me_after_logout.status_code}: {me_after_logout.text}"
    finally:
        import app.core.database as db_module

        db_module.db = _original_db


@pytest.mark.anyio
async def test_login_sets_cookie_attributes():
    """Verify login sets cookies with correct security attributes."""
    mock_db = _create_mock_db()
    test_app, _original_db = _create_test_app(mock_db)

    mock_db.users.find_one = _make_flexible_find_one(TEST_USER)

    try:
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
            async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
                response = await client.post(
                    "/api/auth/login",
                    json={
                        "email": "integration@example.com",
                        "password": TEST_PASSWORD,
                    },
                )

                assert response.status_code == 200

                # Inspect raw Set-Cookie headers for security attributes
                set_cookie_headers = response.headers.get_list("set-cookie")
                assert (
                    len(set_cookie_headers) >= 2
                ), f"Expected at least 2 Set-Cookie headers, got {len(set_cookie_headers)}"

                # Find access_token cookie header
                access_cookie = None
                for header in set_cookie_headers:
                    if header.startswith("access_token="):
                        access_cookie = header.lower()
                        break

                assert access_cookie is not None, "access_token cookie not found"
                assert "httponly" in access_cookie
                assert "path=/" in access_cookie
                assert "samesite=lax" in access_cookie
    finally:
        import app.core.database as db_module

        db_module.db = _original_db


@pytest.mark.anyio
async def test_password_reset_flow():
    """Integration test: forgot-password -> reset-password updates password."""
    mock_db = _create_mock_db()
    test_app, _original_db = _create_test_app(mock_db)

    # forgot-password: user exists
    mock_db.users.find_one = AsyncMock(
        return_value={
            "id": "user-reset-123",
            "email": "reset@example.com",
            "name": "Reset User",
        }
    )
    mock_db.password_reset_tokens.delete_many = AsyncMock()
    mock_db.password_reset_tokens.insert_one = AsyncMock()

    try:
        with patch(
            "app.routers.auth.send_password_reset_email",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send_email:
            async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
                # Step 1: Request password reset
                forgot_response = await client.post(
                    "/api/auth/forgot-password",
                    json={"email": "reset@example.com"},
                )
                assert forgot_response.status_code == 200
                assert "If an account exists" in forgot_response.json()["message"]
                mock_send_email.assert_called_once()

                # Step 2: Reset password with valid token
                future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
                mock_db.password_reset_tokens.find_one = AsyncMock(
                    return_value={
                        "id": "token-reset-123",
                        "user_id": "user-reset-123",
                        "token": "valid-reset-token",
                        "expires_at": future_time,
                    }
                )
                mock_db.users.update_one = AsyncMock()
                mock_db.password_reset_tokens.delete_one = AsyncMock()

                reset_response = await client.post(
                    "/api/auth/reset-password",
                    json={
                        "token": "valid-reset-token",
                        "new_password": "NewSecurePass1!",
                    },
                )
                assert reset_response.status_code == 200
                assert "successfully" in reset_response.json()["message"].lower()
                mock_db.users.update_one.assert_called_once()
                mock_db.password_reset_tokens.delete_one.assert_called_once()
    finally:
        import app.core.database as db_module

        db_module.db = _original_db


@pytest.mark.anyio
async def test_change_password_flow():
    """Integration test: login -> change-password succeeds."""
    mock_db = _create_mock_db()
    test_app, _original_db = _create_test_app(mock_db)

    test_user = TEST_USER.copy()
    mock_db.users.find_one = _make_flexible_find_one(test_user)

    try:
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
            async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
                # Step 1: Login to get auth cookies
                login_response = await client.post(
                    "/api/auth/login",
                    json={
                        "email": "integration@example.com",
                        "password": TEST_PASSWORD,
                    },
                )
                assert login_response.status_code == 200
                auth_headers = _auth_cookie_header(login_response)

                # Step 2: Change password (requires authentication via cookies)
                mock_db.users.update_one = AsyncMock()
                change_response = await client.post(
                    "/api/auth/change-password",
                    headers=auth_headers,
                    json={
                        "current_password": TEST_PASSWORD,
                        "new_password": "NewSecurePass1!",
                    },
                )
                assert change_response.status_code == 200
                assert "successfully" in change_response.json()["message"].lower()
                mock_db.users.update_one.assert_called_once()
    finally:
        import app.core.database as db_module

        db_module.db = _original_db
UTC = timezone.utc
