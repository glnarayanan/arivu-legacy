"""
Tests for bookmarks router endpoints.

Covers: create, list, get, delete, bulk-delete, read-status, bulk-mark-read,
accessed tracking, aged bookmarks, duplicates detection, merge, and related.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.bookmark import is_safe_url

# --- Helpers for cursor mocking ---


def make_cursor(items):
    """Create a mock MongoDB cursor that supports chained .sort().limit().to_list()."""
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=items)
    cursor.sort = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    return cursor


# --- Sample data ---


SAMPLE_BOOKMARK = {
    "id": "bm-1",
    "user_id": "test-user-id",
    "url": "https://example.com/article",
    "title": "Example Article",
    "description": "A test article",
    "domain": "example.com",
    "thumbnail": None,
    "favicon": None,
    "reading_time": 5,
    "read_status": False,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


# ============================================
# POST /bookmarks - Create Bookmark
# ============================================


@pytest.mark.anyio
@patch("app.routers.bookmarks.process_bookmark_content")
async def test_create_bookmark(mock_process, client, mock_db):
    """POST /api/bookmarks creates a bookmark and triggers background processing."""
    # Mock find for quick connections (returns no matches)
    mock_db.bookmarks.find.return_value = make_cursor([])

    response = await client.post(
        "/api/bookmarks",
        json={"url": "https://example.com/new-article"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "bookmark" in data
    assert data["bookmark"]["url"] == "https://example.com/new-article"
    assert data["bookmark"]["domain"] == "example.com"
    assert data["bookmark"]["user_id"] == "test-user-id"
    assert data["bookmark"]["read_status"] is False
    mock_db.bookmarks.insert_one.assert_called_once()
    mock_db.ai_summaries.insert_one.assert_called_once()


@pytest.mark.anyio
async def test_create_bookmark_empty_url(client):
    """POST /api/bookmarks with empty URL returns 422."""
    response = await client.post("/api/bookmarks", json={"url": ""})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_bookmark_localhost_url(client):
    """POST /api/bookmarks with localhost URL returns 422 (SSRF protection)."""
    response = await client.post("/api/bookmarks", json={"url": "http://localhost:8080/admin"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_preview_bookmark_rejects_localhost_url(client):
    """POST /api/bookmarks/preview rejects local network targets."""
    response = await client.post("/api/bookmarks/preview", json={"url": "http://localhost:8080/admin"})
    assert response.status_code == 400


@pytest.mark.anyio
async def test_preview_bookmark_returns_metadata(client, monkeypatch):
    """POST /api/bookmarks/preview returns fetched metadata for safe URLs."""
    monkeypatch.setattr("app.routers.bookmarks.is_safe_url", lambda url, resolve_host=False: (True, ""))

    async def mock_fetch(url, **kwargs):
        return {
            "url": url,
            "title": "Example Preview",
            "description": "Preview description",
            "domain": "example.com",
            "text_content": "word " * 250,
        }

    monkeypatch.setattr("app.routers.bookmarks.fetch_webpage_content", mock_fetch)

    response = await client.post("/api/bookmarks/preview", json={"url": "https://example.com/article"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Example Preview"
    assert data["reading_time"] == 1


@pytest.mark.anyio
async def test_preview_bookmark_rejects_fetch_safety_error(client, monkeypatch):
    """POST /api/bookmarks/preview fails closed when fetch-time validation blocks a URL."""
    monkeypatch.setattr("app.routers.bookmarks.is_safe_url", lambda url, resolve_host=False: (True, ""))

    async def mock_fetch(url, **kwargs):
        raise ValueError("Unsafe URL: Hostname resolves to private or reserved IP addresses")

    monkeypatch.setattr("app.routers.bookmarks.fetch_webpage_content", mock_fetch)

    response = await client.post("/api/bookmarks/preview", json={"url": "https://example.com/redirect"})

    assert response.status_code == 400
    assert "Unsafe URL" in response.json()["detail"]


def test_is_safe_url_rejects_embedded_credentials():
    """URL validation rejects credentials embedded in the authority."""
    safe, error = is_safe_url("https://user:pass@example.com")
    assert safe is False
    assert "embedded credentials" in error


def test_is_safe_url_blocks_dns_private_resolution(monkeypatch):
    """Resolved private IPs are blocked before network fetches."""
    monkeypatch.setattr(
        "socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("10.0.0.10", 443))],
    )

    safe, error = is_safe_url("https://internal.example", resolve_host=True)

    assert safe is False
    assert "private or reserved" in error


# ============================================
# GET /bookmarks - List Bookmarks
# ============================================


@pytest.mark.anyio
async def test_get_bookmarks(client, mock_db):
    """GET /api/bookmarks returns paginated bookmark list for authenticated user."""
    mock_db.bookmarks.find.return_value = make_cursor([SAMPLE_BOOKMARK])
    mock_db.ai_summaries.find.return_value = make_cursor([])

    response = await client.get("/api/bookmarks")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "Example Article"


@pytest.mark.anyio
async def test_get_bookmarks_empty(client, mock_db):
    """GET /api/bookmarks returns empty list when no bookmarks exist."""
    mock_db.bookmarks.find.return_value = make_cursor([])
    mock_db.ai_summaries.find.return_value = make_cursor([])

    response = await client.get("/api/bookmarks")

    assert response.status_code == 200
    data = response.json()
    assert data == []


# ============================================
# GET /bookmarks/{bookmark_id} - Get Single Bookmark
# ============================================


@pytest.mark.anyio
async def test_get_bookmark(client, mock_db):
    """GET /api/bookmarks/{id} returns a single bookmark for the owner."""
    mock_db.bookmarks.find_one = AsyncMock(return_value=SAMPLE_BOOKMARK)
    mock_db.ai_summaries.find_one = AsyncMock(return_value=None)

    response = await client.get("/api/bookmarks/bm-1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "bm-1"
    assert data["title"] == "Example Article"


@pytest.mark.anyio
async def test_get_bookmark_not_found(client, mock_db):
    """GET /api/bookmarks/{id} returns 404 when bookmark doesn't exist."""
    mock_db.bookmarks.find_one = AsyncMock(return_value=None)

    response = await client.get("/api/bookmarks/nonexistent")

    assert response.status_code == 404


# ============================================
# DELETE /bookmarks/{bookmark_id} - Delete Bookmark
# ============================================


@pytest.mark.anyio
async def test_delete_bookmark(client, mock_db):
    """DELETE /api/bookmarks/{id} deletes a bookmark for the owner."""
    mock_result = MagicMock()
    mock_result.deleted_count = 1
    mock_db.bookmarks.delete_one = AsyncMock(return_value=mock_result)

    response = await client.delete("/api/bookmarks/bm-1")

    assert response.status_code == 200
    assert response.json()["message"] == "Bookmark deleted"
    mock_db.ai_summaries.delete_one.assert_called_once()
    mock_db.collections.update_many.assert_called_once()


@pytest.mark.anyio
async def test_delete_bookmark_not_found(client, mock_db):
    """DELETE /api/bookmarks/{id} returns 404 when bookmark doesn't exist."""
    mock_result = MagicMock()
    mock_result.deleted_count = 0
    mock_db.bookmarks.delete_one = AsyncMock(return_value=mock_result)

    response = await client.delete("/api/bookmarks/nonexistent")

    assert response.status_code == 404


# ============================================
# POST /bookmarks/bulk-delete - Bulk Delete
# ============================================


@pytest.mark.anyio
async def test_bulk_delete_bookmarks(client, mock_db):
    """POST /api/bookmarks/bulk-delete deletes multiple bookmarks."""
    mock_result = MagicMock()
    mock_result.deleted_count = 2
    mock_db.bookmarks.delete_many = AsyncMock(return_value=mock_result)

    response = await client.post(
        "/api/bookmarks/bulk-delete",
        json=["bm-1", "bm-2"],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2


# ============================================
# PATCH /bookmarks/{bookmark_id}/read-status - Toggle Read Status
# ============================================


@pytest.mark.anyio
async def test_update_read_status(client, mock_db):
    """PATCH /api/bookmarks/{id}/read-status toggles read status."""
    # find_one_and_update returns the updated document on success
    mock_db.bookmarks.find_one_and_update = AsyncMock(
        return_value={**SAMPLE_BOOKMARK, "read_status": True, "version": 2}
    )

    response = await client.patch(
        "/api/bookmarks/bm-1/read-status",
        params={"read_status": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Read status updated"
    assert data["version"] == 2


@pytest.mark.anyio
async def test_update_read_status_not_found(client, mock_db):
    """PATCH /api/bookmarks/{id}/read-status returns 404 when not found."""
    # find_one_and_update returns None when query doesn't match
    mock_db.bookmarks.find_one_and_update = AsyncMock(return_value=None)
    # find_one also returns None (bookmark doesn't exist at all)
    mock_db.bookmarks.find_one = AsyncMock(return_value=None)

    response = await client.patch(
        "/api/bookmarks/nonexistent/read-status",
        params={"read_status": True},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_read_status_version_conflict(client, mock_db):
    """PATCH /api/bookmarks/{id}/read-status returns 409 on version mismatch."""
    # find_one_and_update returns None (version mismatch)
    mock_db.bookmarks.find_one_and_update = AsyncMock(return_value=None)
    # But bookmark exists (just wrong version)
    mock_db.bookmarks.find_one = AsyncMock(return_value=SAMPLE_BOOKMARK)

    response = await client.patch(
        "/api/bookmarks/bm-1/read-status",
        params={"read_status": True, "version": 99},
    )

    assert response.status_code == 409
    assert "modified by another request" in response.json()["detail"]


# ============================================
# POST /bookmarks/bulk-mark-read - Bulk Mark Read
# ============================================


@pytest.mark.anyio
async def test_bulk_mark_read(client, mock_db):
    """POST /api/bookmarks/bulk-mark-read marks multiple bookmarks as read."""
    mock_result = MagicMock()
    mock_result.modified_count = 3
    mock_db.bookmarks.update_many = AsyncMock(return_value=mock_result)

    response = await client.post(
        "/api/bookmarks/bulk-mark-read",
        json=["bm-1", "bm-2", "bm-3"],
        params={"read_status": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3


# ============================================
# POST /bookmarks/{bookmark_id}/accessed - Track Access
# ============================================


@pytest.mark.anyio
async def test_track_bookmark_access(client, mock_db):
    """POST /api/bookmarks/{id}/accessed tracks bookmark access."""
    mock_db.bookmarks.find_one = AsyncMock(return_value=SAMPLE_BOOKMARK)

    response = await client.post("/api/bookmarks/bm-1/accessed")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "tracked"
    assert "timestamp" in data


@pytest.mark.anyio
async def test_track_bookmark_access_not_found(client, mock_db):
    """POST /api/bookmarks/{id}/accessed returns 404 when not found."""
    mock_db.bookmarks.find_one = AsyncMock(return_value=None)

    response = await client.post("/api/bookmarks/nonexistent/accessed")

    assert response.status_code == 404


# ============================================
# GET /bookmarks/aged - Aged Bookmarks
# ============================================


@pytest.mark.anyio
async def test_get_aged_bookmarks(client, mock_db):
    """GET /api/bookmarks/aged returns stale/old bookmarks."""
    mock_db.bookmarks.find.return_value = make_cursor([SAMPLE_BOOKMARK])

    response = await client.get("/api/bookmarks/aged")

    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "bookmarks" in data
    assert data["count"] == 1


# ============================================
# GET /bookmarks/duplicates/detect - Detect Duplicates
# ============================================


@pytest.mark.anyio
async def test_detect_duplicates(client, mock_db):
    """GET /api/bookmarks/duplicates/detect finds potential duplicate bookmarks."""
    # Two bookmarks with the same URL
    bm1 = {**SAMPLE_BOOKMARK, "id": "bm-1", "url": "https://example.com/article"}
    bm2 = {**SAMPLE_BOOKMARK, "id": "bm-2", "url": "https://example.com/article"}
    mock_db.bookmarks.find.return_value = make_cursor([bm1, bm2])

    response = await client.get("/api/bookmarks/duplicates/detect")

    assert response.status_code == 200
    data = response.json()
    assert "duplicates" in data
    assert len(data["duplicates"]) >= 1
    assert data["duplicates"][0]["type"] == "exact_url"


# ============================================
# POST /bookmarks/merge - Merge Bookmarks
# ============================================


@pytest.mark.anyio
async def test_merge_bookmarks(client, mock_db):
    """POST /api/bookmarks/merge merges two duplicate bookmarks."""
    bm1 = {**SAMPLE_BOOKMARK, "id": "bm-1"}
    bm2 = {**SAMPLE_BOOKMARK, "id": "bm-2"}
    mock_db.bookmarks.find.return_value = make_cursor([bm1, bm2])

    response = await client.post(
        "/api/bookmarks/merge",
        json=["bm-1", "bm-2"],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Bookmarks merged"
    assert data["kept_bookmark"]["id"] == "bm-1"
    mock_db.bookmarks.delete_many.assert_called_once()
    mock_db.ai_summaries.delete_many.assert_called_once()


@pytest.mark.anyio
async def test_merge_bookmarks_too_few(client, mock_db):
    """POST /api/bookmarks/merge with fewer than 2 IDs returns 400."""
    response = await client.post(
        "/api/bookmarks/merge",
        json=["bm-1"],
    )

    assert response.status_code == 400


# ============================================
# GET /bookmarks/{bookmark_id}/related - Related Bookmarks
# ============================================


@pytest.mark.anyio
async def test_get_related_bookmarks_no_embedding(client, mock_db):
    """GET /api/bookmarks/{id}/related returns empty when no embedding exists."""
    mock_db.bookmarks.find_one = AsyncMock(return_value={"id": "bm-1", "title": "Test", "embedding": None})

    response = await client.get("/api/bookmarks/bm-1/related")

    assert response.status_code == 200
    data = response.json()
    assert data["related"] == []
    assert "message" in data


@pytest.mark.anyio
async def test_get_related_bookmarks_not_found(client, mock_db):
    """GET /api/bookmarks/{id}/related returns 404 when bookmark doesn't exist."""
    mock_db.bookmarks.find_one = AsyncMock(return_value=None)

    response = await client.get("/api/bookmarks/nonexistent/related")

    assert response.status_code == 404
