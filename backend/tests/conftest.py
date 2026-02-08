"""
Shared test fixtures for Arivu backend tests.

Provides mock auth, mock database, test app, and async HTTP client.
Reusable across all router test modules (collections, analytics, resurfacing).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_database
from app.core.dependencies import get_current_user
from app.routers.collections import router as collections_router
from app.routers.analytics import router as analytics_router
from app.routers.resurfacing import router as resurfacing_router
from app.routers.auth import router as auth_router

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter storage between tests to prevent leaking state."""
    from app.core.dependencies import limiter

    limiter.reset()
    yield
    limiter.reset()


MOCK_USER = {
    "id": "test-user-id",
    "email": "test@example.com",
    "name": "Test User",
}


@pytest.fixture
def mock_user():
    return MOCK_USER.copy()


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database with async collection methods."""
    db = MagicMock()

    # Collections
    db.collections = MagicMock()
    db.collections.insert_one = AsyncMock()
    db.collections.find = MagicMock()  # .find() returns cursor, needs chaining
    db.collections.update_one = AsyncMock()

    # Bookmarks (for resurfacing/memory-jogger tests in Plan 02)
    db.bookmarks = MagicMock()
    db.bookmarks.find = MagicMock()
    db.bookmarks.find_one = AsyncMock()
    db.bookmarks.update_one = AsyncMock()

    # AI summaries (for resurfacing tests in Plan 02)
    db.ai_summaries = MagicMock()
    db.ai_summaries.find = MagicMock()
    db.ai_summaries.find_one = AsyncMock()

    # Users (for auth tests in Phase 5)
    db.users = MagicMock()
    db.users.find_one = AsyncMock()
    db.users.insert_one = AsyncMock()
    db.users.update_one = AsyncMock()

    # Password reset tokens (for auth tests in Phase 5)
    db.password_reset_tokens = MagicMock()
    db.password_reset_tokens.find_one = AsyncMock()
    db.password_reset_tokens.insert_one = AsyncMock()
    db.password_reset_tokens.delete_one = AsyncMock()
    db.password_reset_tokens.delete_many = AsyncMock()

    return db


@pytest.fixture
def app(mock_db):
    """Create test FastAPI app with collections router and mock dependencies."""
    test_app = FastAPI()
    api_router = APIRouter(prefix="/api")
    api_router.include_router(collections_router)
    api_router.include_router(analytics_router)
    api_router.include_router(resurfacing_router)
    api_router.include_router(auth_router)
    test_app.include_router(api_router)

    # Set up rate limiter (required for auth router's slowapi decorators)
    from app.core.dependencies import limiter

    test_app.state.limiter = limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Override auth dependency
    test_app.dependency_overrides[get_current_user] = lambda: MOCK_USER

    # Override database: set module-level db variable so get_database() returns our mock
    import app.core.database as db_module

    _original_db = db_module.db
    db_module.db = mock_db

    yield test_app

    # Restore
    db_module.db = _original_db
    test_app.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    """Async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def auth_app(mock_db):
    """Test app for auth tests WITHOUT auth override (tests login/signup flow)."""
    test_app = FastAPI()
    api_router_local = APIRouter(prefix="/api")
    api_router_local.include_router(auth_router)
    test_app.include_router(api_router_local)

    # Set up rate limiter
    from app.core.dependencies import limiter

    test_app.state.limiter = limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Override database
    import app.core.database as db_module

    _original_db = db_module.db
    db_module.db = mock_db

    yield test_app

    db_module.db = _original_db


@pytest.fixture
async def auth_client(auth_app):
    """Async HTTP client for auth testing (no auth override)."""
    async with AsyncClient(
        transport=ASGITransport(app=auth_app), base_url="http://test"
    ) as ac:
        yield ac
