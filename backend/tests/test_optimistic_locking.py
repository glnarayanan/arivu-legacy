"""
Unit tests for optimistic locking logic paths (mock-based).

Verifies that the bookmarks router correctly:
- Returns 200 with incremented version on correct version match
- Returns 409 Conflict when version is stale
- Allows updates without version parameter (backward compatibility)
- Returns 404 when bookmark doesn't exist at all
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient

from app.routers.bookmarks import router as bookmarks_router
from app.core.dependencies import get_current_user
import app.core.database as db_module

MOCK_USER = {
    "id": "test-user-id",
    "email": "test@example.com",
    "name": "Test User",
}

SAMPLE_BOOKMARK = {
    "id": "bm-1",
    "user_id": "test-user-id",
    "url": "https://example.com/article",
    "title": "Example Article",
    "domain": "example.com",
    "read_status": False,
    "version": 1,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def mock_db():
    """Create a minimal mock MongoDB for optimistic locking tests."""
    db = MagicMock()
    db.bookmarks = MagicMock()
    db.bookmarks.find_one = AsyncMock()
    db.bookmarks.find_one_and_update = AsyncMock()
    db.bookmarks.insert_one = AsyncMock()
    db.bookmarks.update_one = AsyncMock()
    db.ai_summaries = MagicMock()
    db.ai_summaries.find_one = AsyncMock()
    return db


@pytest.fixture
def bookmarks_app(mock_db):
    """Test app with bookmarks router for optimistic locking tests."""
    test_app = FastAPI()
    api_router = APIRouter(prefix="/api")
    api_router.include_router(bookmarks_router)
    test_app.include_router(api_router)
    test_app.dependency_overrides[get_current_user] = lambda: MOCK_USER

    # Set up rate limiter (required for bookmarks router decorators)
    from app.core.dependencies import limiter

    test_app.state.limiter = limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    _original_db = db_module.db
    db_module.db = mock_db
    yield test_app
    db_module.db = _original_db
    test_app.dependency_overrides.clear()


@pytest.fixture
async def bookmarks_client(bookmarks_app):
    """Async HTTP client for bookmarks optimistic locking tests."""
    async with AsyncClient(
        transport=ASGITransport(app=bookmarks_app), base_url="http://test"
    ) as ac:
        yield ac


# ============================================
# Optimistic Locking: Version-Controlled Updates
# ============================================


@pytest.mark.anyio
async def test_update_read_status_with_correct_version_succeeds(
    bookmarks_client, mock_db
):
    """PATCH with correct version returns 200 and incremented version."""
    mock_db.bookmarks.find_one_and_update = AsyncMock(
        return_value={**SAMPLE_BOOKMARK, "read_status": True, "version": 2}
    )

    response = await bookmarks_client.patch(
        "/api/bookmarks/bm-1/read-status",
        params={"read_status": True, "version": 1},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Read status updated"
    assert data["version"] == 2

    # Verify the query included version matching
    call_args = mock_db.bookmarks.find_one_and_update.call_args
    query = call_args[0][0]
    assert query["id"] == "bm-1"
    assert query["user_id"] == "test-user-id"
    # Should have $or clause with version match and backward compat
    assert "$or" in query
    version_conditions = query["$or"]
    assert {"version": 1} in version_conditions
    assert {"version": {"$exists": False}} in version_conditions


@pytest.mark.anyio
async def test_update_read_status_with_stale_version_returns_409(
    bookmarks_client, mock_db
):
    """PATCH with stale version returns 409 Conflict when bookmark exists but version mismatches."""
    # find_one_and_update returns None (version mismatch -- query didn't match)
    mock_db.bookmarks.find_one_and_update = AsyncMock(return_value=None)
    # Bookmark exists, but with a different version
    mock_db.bookmarks.find_one = AsyncMock(
        return_value={**SAMPLE_BOOKMARK, "version": 5}
    )

    response = await bookmarks_client.patch(
        "/api/bookmarks/bm-1/read-status",
        params={"read_status": True, "version": 1},
    )

    assert response.status_code == 409
    assert "modified by another request" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_read_status_without_version_succeeds(
    bookmarks_client, mock_db
):
    """PATCH without version parameter succeeds (backward compatibility)."""
    mock_db.bookmarks.find_one_and_update = AsyncMock(
        return_value={**SAMPLE_BOOKMARK, "read_status": True, "version": 2}
    )

    response = await bookmarks_client.patch(
        "/api/bookmarks/bm-1/read-status",
        params={"read_status": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Read status updated"
    assert data["version"] == 2

    # Verify the query did NOT include version matching ($or clause absent)
    call_args = mock_db.bookmarks.find_one_and_update.call_args
    query = call_args[0][0]
    assert "$or" not in query
    assert query["id"] == "bm-1"
    assert query["user_id"] == "test-user-id"


@pytest.mark.anyio
async def test_update_read_status_nonexistent_bookmark_returns_404(
    bookmarks_client, mock_db
):
    """PATCH on nonexistent bookmark returns 404."""
    # find_one_and_update returns None (no match at all)
    mock_db.bookmarks.find_one_and_update = AsyncMock(return_value=None)
    # find_one also returns None (bookmark doesn't exist)
    mock_db.bookmarks.find_one = AsyncMock(return_value=None)

    response = await bookmarks_client.patch(
        "/api/bookmarks/nonexistent/read-status",
        params={"read_status": True, "version": 1},
    )

    assert response.status_code == 404
    assert "Bookmark not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_read_status_version_field_incremented_in_update(
    bookmarks_client, mock_db
):
    """Verify the update operation includes $inc for version field."""
    mock_db.bookmarks.find_one_and_update = AsyncMock(
        return_value={**SAMPLE_BOOKMARK, "read_status": False, "version": 3}
    )

    response = await bookmarks_client.patch(
        "/api/bookmarks/bm-1/read-status",
        params={"read_status": False, "version": 2},
    )

    assert response.status_code == 200
    assert response.json()["version"] == 3

    # Verify $inc was used for version
    call_args = mock_db.bookmarks.find_one_and_update.call_args
    update_doc = call_args[0][1]
    assert "$inc" in update_doc
    assert update_doc["$inc"]["version"] == 1
    assert "$set" in update_doc
    assert update_doc["$set"]["read_status"] is False
