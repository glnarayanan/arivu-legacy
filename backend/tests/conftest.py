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

    return db


@pytest.fixture
def app(mock_db):
    """Create test FastAPI app with collections router and mock dependencies."""
    test_app = FastAPI()
    api_router = APIRouter(prefix="/api")
    api_router.include_router(collections_router)
    api_router.include_router(analytics_router)
    test_app.include_router(api_router)

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
