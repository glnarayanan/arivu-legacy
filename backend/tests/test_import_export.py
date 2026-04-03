"""
Tests for import/export router endpoints.

Covers: import bookmarks, get import jobs, get single job, job not found,
export bookmarks, backup bookmarks.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


# Cursor mock factory for chained MongoDB queries
def make_cursor_mock(data):
    """Create a mock that supports .sort(...).limit(...).to_list(None) chaining."""
    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=data)
    return cursor


@pytest.mark.anyio
async def test_import_bookmarks(client, mock_db):
    """POST /api/bookmarks/import accepts HTML file and creates import job."""
    html_content = """
    <!DOCTYPE NETSCAPE-Bookmark-file-1>
    <DL><p>
        <DT><A HREF="https://example.com">Example</A>
        <DT><A HREF="https://python.org">Python</A>
    </DL><p>
    """
    mock_db.bookmarks.insert_one = AsyncMock()
    mock_db.ai_summaries.insert_one = AsyncMock()
    mock_db.import_jobs.insert_one = AsyncMock()

    response = await client.post(
        "/api/bookmarks/import",
        content=html_content.encode("utf-8"),
    )
    assert response.status_code == 200

    data = response.json()
    assert data["count"] == 2
    assert "import_job_id" in data
    assert "Imported 2 bookmarks" in data["message"]


@pytest.mark.anyio
async def test_get_import_jobs(client, mock_db):
    """GET /api/import-jobs returns list of import jobs for user."""
    mock_jobs = [
        {
            "id": "job-1",
            "user_id": "test-user-id",
            "total_bookmarks": 10,
            "status": "completed",
            "created_at": "2024-01-01T00:00:00Z",
        }
    ]
    mock_db.import_jobs.find.return_value = make_cursor_mock(mock_jobs)

    response = await client.get("/api/import-jobs")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "job-1"


@pytest.mark.anyio
async def test_get_import_job(client, mock_db):
    """GET /api/import-jobs/{id} returns specific import job."""
    mock_db.import_jobs.find_one = AsyncMock(
        return_value={
            "id": "job-1",
            "user_id": "test-user-id",
            "total_bookmarks": 10,
            "content_fetched": 8,
            "ai_processed": 5,
            "failed": 2,
            "status": "completed",
        }
    )

    response = await client.get("/api/import-jobs/job-1")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "job-1"
    assert data["status"] == "completed"


@pytest.mark.anyio
async def test_get_import_job_not_found(client, mock_db):
    """GET /api/import-jobs/{id} returns 404 for non-existent job."""
    mock_db.import_jobs.find_one = AsyncMock(return_value=None)

    response = await client.get("/api/import-jobs/nonexistent")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_export_bookmarks(client, mock_db):
    """GET /api/bookmarks/export returns HTML bookmark file."""
    mock_bookmarks = [
        {
            "url": "https://example.com",
            "title": "Example Site",
            "created_at": "2024-01-01T00:00:00+00:00",
        },
    ]
    mock_db.bookmarks.find.return_value = make_cursor_mock(mock_bookmarks)

    response = await client.get("/api/bookmarks/export")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "NETSCAPE-Bookmark-file-1" in response.text
    assert 'HREF="https://example.com"' in response.text


@pytest.mark.anyio
async def test_backup_bookmarks(client, mock_db):
    """POST /api/bookmarks/backup creates backup in requested format."""
    mock_bookmarks = [
        {
            "id": "b1",
            "url": "https://example.com",
            "title": "Example",
            "domain": "example.com",
            "created_at": "2024-01-01T00:00:00+00:00",
            "read_status": False,
            "reading_time": 3,
        },
    ]
    mock_db.bookmarks.find.return_value = make_cursor_mock(mock_bookmarks)
    mock_db.ai_summaries.find.return_value = MagicMock(to_list=AsyncMock(return_value=[]))
    mock_db.notes.find.return_value = MagicMock(to_list=AsyncMock(return_value=[]))

    response = await client.post(
        "/api/bookmarks/backup",
        json={"format": "json", "include_notes": True, "include_ai_summaries": True},
    )
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    # Verify JSON content
    import json

    data = json.loads(response.text)
    assert data["total_bookmarks"] == 1
    assert len(data["bookmarks"]) == 1


@pytest.mark.anyio
async def test_import_rejects_unauthenticated(mock_db):
    """Import/export endpoints reject unauthenticated requests."""
    from app.routers.import_export import router as ie_router
    from fastapi import APIRouter, FastAPI
    from httpx import ASGITransport, AsyncClient

    # Create test app WITHOUT auth override
    test_app = FastAPI()
    api = APIRouter(prefix="/api")
    api.include_router(ie_router)
    test_app.include_router(api)

    # Set up rate limiter (required for import endpoint)
    from app.core.dependencies import limiter

    test_app.state.limiter = limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Override database
    import app.core.database as db_module

    _original_db = db_module.db
    db_module.db = mock_db

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.post("/api/bookmarks/import", content=b"test")
        assert response.status_code == 401

    db_module.db = _original_db


@pytest.mark.anyio
async def test_import_bookmarks_rejects_large_files(client):
    """POST /api/bookmarks/import rejects files over 50MB."""
    # Create a payload that's just over 50MB
    large_content = b"x" * (50 * 1024 * 1024 + 1)  # 50MB + 1 byte

    response = await client.post(
        "/api/bookmarks/import",
        content=large_content,
    )
    assert response.status_code == 413
    assert "50MB" in response.json()["detail"]
